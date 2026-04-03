# Some UI Help Stuff

## Fetch user location in browser

```
function getLocation() {
  if (!navigator.geolocation) {
    console.error("Geolocation is not supported by your browser");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      
      console.log(`Latitude: ${lat}, Longitude: ${lng}`);
      alert(`You are at: ${lat}, ${lng}`);
    },
    (error) => {
      console.error(`Error (${error.code}): ${error.message}`);
    }
  );
}

getLocation();
```
