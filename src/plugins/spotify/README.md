# Load album art from Spotify

Requires a Free Spotify Client ID, Secret and Auth code

Go to: https://developer.spotify.com/dashboard
- Click "Create app":
- Supply name and description (i.e. InkyPi)
- As "Redirect URL" enter: http://127.0.0.1:8080/callback
- Copy the value under Client ID, you will need this later. Ie. xxxxx
- Click View client secret, Copy the value under Client secret. You will need this later. Ie. yyyyyy

Important: Go into an incognito window (since Spotify Auth codes can only be used once - so to avoid any errors use incognito)
Start some music on your Spotify account. 

Open the Spotify plugin in Inkypi.
- Click "Spotify Advanced Setup (optional)"
- Enter the Client ID and Client Secret.
- Click "Open Spotify login". This will open a new browser tab with a Spotify login page (if you are NOT prompted to login to Spotify, close and retry in Incognito)
- This will redirect you to a nonexisting page. With this URL  http://127.0.0.1:8080/callback?code=zzzzz   The zzzzz is the Auth code

Go back to the InkyPi tab and enter the Authorization Code the zzzz in the field for that.

Press "Update now"


