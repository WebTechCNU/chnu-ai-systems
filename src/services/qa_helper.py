import json
import openai
from typing import List, Dict, Any, Optional
import os
from src.infrastructure.models import TestCase, IntentResult, PageIssue, BugReport
import re
import httpx
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import logging
from dotenv import load_dotenv

load_dotenv()

OPEN_API_KEY = os.getenv("OPEN_API_KEY")

class LLMClient:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4o"  # or gpt-3.5-turbo for lower cost
    
    async def generate(self, prompt: str, system_prompt: str = None, temperature: float = 0.3) -> str:
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature
        )
        
        print("prompt: ", prompt)
        print("response: ", response.choices[0].message.content)

        return response.choices[0].message.content
    
    async def generate_json(self, prompt: str, system_prompt: str = None) -> Dict:
        if system_prompt:
            system_prompt += " Return ONLY valid JSON without any markdown formatting or extra text."
        else:
            system_prompt = "Return ONLY valid JSON without any markdown formatting or extra text."
        
        response = await self.generate(prompt, system_prompt, temperature=0.1)
        return json.loads(response.strip())
    

class IntentClassifier:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    async def classify(self, prompt: str) -> IntentResult:
        # First, try regex patterns for quick classification
        prompt_lower = prompt.lower()
        
        # URL patterns
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        urls = re.findall(url_pattern, prompt)
        
        # Web page indicators
        web_indicators = ['page', 'website', 'web page', 'browser', 'html', 'css', 
                         'console error', 'dom', 'ui', 'frontend', 'visual']
        
        # API indicators  
        api_indicators = ['endpoint', 'api', 'rest', 'graphql', 'http request', 
                         'post', 'get', 'put', 'delete', 'status code']
        
        # Log indicators
        log_indicators = ['log', 'logs', 'error log', 'application log', 'stack trace',
                         'exception', 'traceback', 'logging']
        
        # Count matches
        web_score = sum(1 for word in web_indicators if word in prompt_lower)
        api_score = sum(1 for word in api_indicators if word in prompt_lower)
        log_score = sum(1 for word in log_indicators if word in prompt_lower)
        
        scores = {
            TestCase.WEB_PAGE: web_score,
            TestCase.API_ENDPOINT: api_score,
            TestCase.LOGS: log_score
        }
        
        # If pattern matching is confident enough
        max_score = max(scores.values())
        if max_score >= 2 and max_score > scores[TestCase.UNKNOWN]:
            best_case = max(scores, key=scores.get)
            extracted_data = self._extract_basic_data(prompt, best_case, urls)
            
            return IntentResult(
                case=best_case,
                extracted_data=extracted_data,
                confidence=0.8
            )
        
        # Otherwise use LLM for classification
        return await self._llm_classify(prompt, urls)
    
    def _extract_basic_data(self, prompt: str, case: TestCase, urls: list) -> Dict[str, Any]:
        data = {}
        
        if urls:
            data["url"] = urls[0]
        
        if case == TestCase.API_ENDPOINT:
            # Extract HTTP method if specified
            method_match = re.search(r'\b(GET|POST|PUT|DELETE|PATCH)\b', prompt, re.IGNORECASE)
            if method_match:
                data["method"] = method_match.group(1).upper()
            else:
                data["method"] = "GET"
        
        return data
    
    async def _llm_classify(self, prompt: str, urls: list) -> IntentResult:
        system_prompt = """
        You are an intent classifier for a QA testing assistant. 
        Classify the user request into one of these categories:
        - web_page: testing a web page for UI issues, console errors, HTML problems
        - api_endpoint: testing an API endpoint for correct responses, status codes, data validation
        - logs: analyzing application logs for errors, exceptions, or issues
        
        Extract relevant data:
        - For web_page: URL
        - For api_endpoint: URL, HTTP method (if specified)
        - For logs: the log content or reference to log location
        
        Return JSON with: {"case": "web_page|api_endpoint|logs", "extracted_data": {...}}
        """
        
        result = await self.llm.generate_json(prompt, system_prompt)
        
        case = TestCase(result.get("case", "unknown"))
        extracted_data = result.get("extracted_data", {})
        
        # If no URL extracted but we found one via regex
        if not extracted_data.get("url") and urls:
            extracted_data["url"] = urls[0]
        
        return IntentResult(
            case=case,
            extracted_data=extracted_data,
            confidence=0.9
        )
    

class WebTester:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.logger = logging.getLogger(__name__)
    
    async def test_page(self, url: str) -> BugReport:
        # Collect page data
        page_data = await self._extract_page_data(url)
        
        # Analyze with LLM
        bug_report = await self._analyze_with_llm(page_data, url)
        
        return bug_report
    
    async def _extract_page_data(self, url: str) -> Dict:
        """Extract HTML content and console errors"""
        data = {
            "url": url,
            "html_content": "",
            "console_errors": [],
            "status_code": None,
            "page_title": ""
        }
        
        # Get HTML content
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, follow_redirects=True)
                data["status_code"] = response.status_code
                data["html_content"] = response.text[:50000]  # Limit size
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                data["page_title"] = soup.title.string if soup.title else "No title"
                
                # Basic HTML validation
                issues = []
                if not soup.find('html'):
                    issues.append("Missing <html> tag")
                if not soup.find('head'):
                    issues.append("Missing <head> tag")
                if not soup.find('body'):
                    issues.append("Missing <body> tag")
                
                data["html_validation_issues"] = issues
                
            except Exception as e:
                data["error"] = str(e)
                return data
        
        # Get console errors using Selenium
        data["console_errors"] = await self._get_console_errors(url)
        
        return data
    
    async def _get_console_errors(self, url: str) -> List[str]:
        """Launch headless browser and capture console errors"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        console_errors = []
        
        try:
            driver.get(url)
            logs = driver.get_log("browser")
            
            for entry in logs:
                if entry['level'] in ['SEVERE', 'WARNING']:
                    console_errors.append(f"{entry['level']}: {entry['message']}")
            
            # Also check for common JS errors
            js_errors = driver.execute_script("""
                return window.jsErrors || [];
            """)
            console_errors.extend(js_errors)
            
        except Exception as e:
            self.logger.error(f"Selenium error: {e}")
        finally:
            driver.quit()
        
        return console_errors[:20]  # Limit number of errors
    
    async def _analyze_with_llm(self, page_data: Dict, url: str) -> BugReport:
        """Use LLM to analyze page issues and create bug report"""
        
        prompt = f"""
        Analyze this web page for QA testing purposes:
        
        URL: {url}
        Status Code: {page_data.get('status_code')}
        Page Title: {page_data.get('page_title')}
        
        HTML Validation Issues: {', '.join(page_data.get('html_validation_issues', []))}
        
        Console Errors: 
        {chr(10).join(page_data.get('console_errors', []))}
        
        HTML Snippet (first 3000 chars):
        {page_data.get('html_content', '')[:3000]}
        
        Based on this analysis, identify the most critical bugs/issues. If there are no significant issues, indicate that the page is working correctly.
        
        Return a JSON bug report list (list of items of strict name 'bug_report') each with:
        - title: Brief bug title
        - description: Detailed description including what's wrong
        - steps_to_reproduce: List of steps to reproduce
        - expected_result: What should happen
        - actual_result: What actually happens
        - severity: critical/major/minor
        """
        
        result = await self.llm.generate_json(prompt)
        bug_reports = [BugReport(**item) for item in result["bug_report"]]
        return bug_reports
    

class APITester:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    async def test_endpoint(self, url: str, method: str = "GET", 
                           headers: Optional[Dict] = None, 
                           body: Optional[Dict] = None) -> BugReport:
        """Test API endpoint and return bug report"""
        
        # Make the request
        response_data = await self._make_request(url, method, headers, body)
        
        # Analyze with LLM
        bug_report = await self._analyze_response(url, method, response_data)
        
        return bug_report
    
    async def _make_request(self, url: str, method: str, 
                           headers: Optional[Dict], 
                           body: Optional[Dict]) -> Dict:
        """Execute HTTP request"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, json=body, headers=headers)
                elif method == "PUT":
                    response = await client.put(url, json=body, headers=headers)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    response = await client.request(method, url, json=body, headers=headers)
                
                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.text[:10000],  # Limit size
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "success": response.status_code < 400
                }
                
            except Exception as e:
                return {
                    "error": str(e),
                    "success": False
                }
    
    async def _analyze_response(self, url: str, method: str, response_data: Dict) -> BugReport:
        """Use LLM to analyze API response"""
        
        prompt = f"""
        Analyze this API endpoint test result:
        
        Endpoint: {method} {url}
        
        Response:
        - Status Code: {response_data.get('status_code', 'No response')}
        - Response Time: {response_data.get('response_time_ms', 'N/A')} ms
        - Success: {response_data.get('success', False)}
        
        Response Body (truncated):
        {response_data.get('body', 'No body')[:2000]}
        
        Response Headers: {response_data.get('headers', {})}
        
        Error (if any): {response_data.get('error', 'None')}
        
        Evaluate if this API is working correctly. Consider:
        1. Appropriate status codes (2xx for success, 4xx for client errors, 5xx for server errors)
        2. Response time (should be < 500ms for typical endpoints)
        3. Response structure and data validity
        4. Proper error messages
        
        Return a JSON bug report. If everything is correct, create a report indicating that.
        """
        
        result = await self.llm.generate_json(prompt)
        return BugReport(**result)
    
    
class LogAnalyzer:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    async def analyze_logs(self, log_content: str) -> BugReport:
        """Analyze application logs for issues"""
        
        # Process logs (extract errors, patterns)
        processed_logs = self._preprocess_logs(log_content)
        
        # Analyze with LLM
        bug_report = await self._analyze_with_llm(processed_logs)
        
        return bug_report
    
    def _preprocess_logs(self, log_content: str) -> Dict:
        """Extract key information from logs"""
        lines = log_content.strip().split('\n')
        
        errors = []
        warnings = []
        exceptions = []
        
        for line in lines:
            line_lower = line.lower()
            if 'error' in line_lower or 'exception' in line_lower:
                errors.append(line)
            elif 'warn' in line_lower:
                warnings.append(line)
            if 'traceback' in line_lower or 'stack trace' in line_lower:
                exceptions.append(line)
        
        return {
            "total_lines": len(lines),
            "errors": errors[:20],  # Limit
            "warnings": warnings[:20],
            "exceptions": exceptions[:10],
            "raw_sample": log_content[:5000]  # First 5000 chars
        }
    
    async def _analyze_with_llm(self, processed_logs: Dict) -> BugReport:
        """Use LLM to find issues in logs"""
        
        prompt = f"""
        Analyze these application logs and identify any bugs or issues:
        
        Total log lines: {processed_logs['total_lines']}
        
        Errors found ({len(processed_logs['errors'])}):
        {chr(10).join(processed_logs['errors'][:10])}
        
        Warnings found ({len(processed_logs['warnings'])}):
        {chr(10).join(processed_logs['warnings'][:5])}
        
        Exceptions/Stack traces:
        {chr(10).join(processed_logs['exceptions'][:3])}
        
        Raw log sample:
        {processed_logs['raw_sample']}
        
        Identify the most critical issues in these logs. For each issue, provide:
        - What error occurred
        - Possible root cause
        - Recommended fix
        
        Return a JSON bug report describing the most critical issue found.
        If no issues found, return a report stating that the logs appear healthy.
        """
        
        result = await self.llm.generate_json(prompt)
        return BugReport(**result)