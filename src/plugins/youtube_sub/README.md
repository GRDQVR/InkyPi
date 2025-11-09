# Load subscribers from an Youtube channel

Loads number of subscribers from an Youtube channel

Requires a Free Youtube Data Api V3 key from API KEY from https://console.cloud.google.com
 
- Go to  https://console.cloud.google.com
- In the top menu to the right of the Google Cloud logo select an existing project or create a "New project" and name it.
- In the left menu select "APIs & Services" | "Library"
- Scroll down to "Youtube Data API v3" select it and press the blue "Enable" button
- In the left menu select "APIs & Services" | "Credentials"
- Click "Create Credentials" in the top menu, Select "API Key".
- Name your Credentials something i.e. InkyPiCredentials. All the other settings are ok, no need to change (but you could restrict your key if needed). Click Create
- In the section API Keys click on your key i.e. InkyPiCredentials if you named it that. 
- Click "Show key" in the menu on the right. It is listed as "Your API Key"
- Save your access key in `/.env` file as `YOUTUBE_SECRET=`
