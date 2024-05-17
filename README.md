# Silly_Ninja

## DESCRIPTION
A multiplayer co-op game made with __Pygame__ and __Socket__, assets credit goes to _DaFluffyPotato_.

## CONTROLS
- A, Left Arrow: Move to the left
- D, Right Arrow: Move to the right
- Space, Up Arrow: Jump
- L.Shift, R.Shift: Dash/Attack
- ESC: Back out

## REQUIRED EXTERNAL MODULES
Install modules by the command `python -m pip install [module_name]` or `python3 -m pip install [module_name]`.
- pygame
- PyInstaller
- pyperclip
- gtk (Linux only)
- PyQt4 (Linux only)

## INSTALLATION
### From Source
- Clone the repo with `git clone https://github.com/constance012/Silly_Ninja.git`.
- Install all required modules from the above section.
- Navigate to `Silly Ninja\assets\fonts` and install all required fonts.
- Run these following commands:
```
cd Silly_Ninja/‘Silly Ninja’
For Windows: python silly_ninja.py
For Linux: python3 silly_ninja.py
```
### From Executables
- Navigate to `Silly Ninja\assets\fonts` and install all required fonts.
- Extract the content of `Silly Ninja\executables.zip`.
- Navigate to `Silly Ninja\executables`.
- If you want to open the map editor, go to `map_editor_win_x64` and run `map_editor.exe`.
- For the game, go to `silly_ninja_win_x64` and run `silly_ninja.exe`.
 

## MULTIPLAYER INSTRUCTION
Because the game only supports multiplayer through Local Area Network (LAN), there're couple of ways to establish connections and play with your friends:
- You and your friends must be on the same network or Wifi, so that the host's IP can be discovered by other clients.
- Using third party software that provide the ability to create your own virtual networks, such as _Hamachi_, _RadminVPN_ or _ZeroTier_,... just to name a few. Then you and your friend can join the same network and establish connection. This is actually the prefer method because y'all can connect to each other from anywhere on the globe, as long as your device remain in that said virtual network.

After that, open the game and press the `Join` or `Host` button, depends on your situation:
- For the host, enter local IP on your network to the `IP` field, and enter a port number to the `Port` field (must be greater than 1000). After that, choose a nickname and press `Start`, you'll be in the lobby if the server starts successfully.
- For the client, enter the Host's IP and port to both fields. After that, pick a nickname and press `Join`, you'll be in the lobby if the connection establishes successfully.
- After all clients have joined the lobby and ready, indicates by their slots borders turn green, the Host then can start the game by pressing the `Launch` button.

## NOTES
- Before running the game, you must navigate to the `fonts` folder to install all the fonts contained within it.
- Ensure that all required libraries and modules are installed in order to run the game.

## CREDITS
Special thanks to [___DaFluffyPotato___](https://www.youtube.com/@DaFluffyPotato) for the gorgeous image assets and audio.

## CONTRIBUTIONS
@Hikiyoshi - Programmer, Tester.
@constance012 - Programmer, Networking, UI Design.

## IN GAME CAPTURES
![Main Menu](https://private-user-images.githubusercontent.com/96867270/331322071-fd2297b5-96d2-4295-a5b2-c379cd95bbae.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MTU5Mjg1ODQsIm5iZiI6MTcxNTkyODI4NCwicGF0aCI6Ii85Njg2NzI3MC8zMzEzMjIwNzEtZmQyMjk3YjUtOTZkMi00Mjk1LWE1YjItYzM3OWNkOTViYmFlLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDA1MTclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQwNTE3VDA2NDQ0NFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTQwMTEzMzdkMDNmYTZjY2RlZWFiMDcwZmJmOGFiNzI0Mjk3MjFhN2EzZGIzMzI3NjM5MzllMmZiOTJiNTA0MzImWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JmFjdG9yX2lkPTAma2V5X2lkPTAmcmVwb19pZD0wIn0.SO71XJMyowEFEOrW6aiBVu96MoTp70aUoU63SA7zrPI)
![In Game](https://private-user-images.githubusercontent.com/96867270/331322655-547c06de-fefa-4a28-b791-44b873f484e3.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MTU5Mjg1ODQsIm5iZiI6MTcxNTkyODI4NCwicGF0aCI6Ii85Njg2NzI3MC8zMzEzMjI2NTUtNTQ3YzA2ZGUtZmVmYS00YTI4LWI3OTEtNDRiODczZjQ4NGUzLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDA1MTclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQwNTE3VDA2NDQ0NFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTU4OWYwOTkyNDQ5NDM0MGFhNmU1NTdmYWZhYjM4ZGU0NmY3ZWVjODMxOTc0OWFkMzIyMmMzMWE2ZTNlOWRiMTkmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JmFjdG9yX2lkPTAma2V5X2lkPTAmcmVwb19pZD0wIn0.eo7fj2nDd5W88Df_wnM734AMFKJRahQi6j-9Z07iQYs)
