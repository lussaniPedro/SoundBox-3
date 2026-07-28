import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import time
import pygame
import colorama
import threading
import sys
import select
import subprocess

cava_process = None

print(colorama.Fore.GREEN + colorama.Style.BRIGHT)

def clear_terminal():
    subprocess.run("cls" if os.name == "nt" else "clear")

def start_cava():
    global cava_process

    if cava_process is not None:
        return

    cava_process = subprocess.Popen(
        [
            "konsole",
            "--separate",
            "-e",
            "cava"
        ]
    )


def stop_cava():
    global cava_process

    if cava_process is not None:
        cava_process.terminate()

        try:
            cava_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            cava_process.kill()

        cava_process = None

def render_player_ui(song_name, playlist_name, status="Playing", loop_mode="None"):
    clear_terminal()
    print("🎧 SoundBox 3 📦\n")

    print(f"🎵 Now playing: {song_name}")
    print(f"📁 Playlist: {playlist_name}")
    print(f"⏯️ Status: {status}")
    print(f"🔁 Loop: {loop_mode.capitalize()}\n")

    if status == "Playing":
        print("[P] Pause | [B] Previous | [N] Next | [L] Loop | [S] Stop")
    else:
        print("[R] Resume | [B] Previous | [N] Next | [L] Loop | [S] Stop")

    print("> ", end="", flush=True)

def render_loop_menu(song_name, playlist_name, status="Playing", loop_mode="None"):
    clear_terminal()
    print("🎧 SoundBox 3 📦\n")

    print(f"🎵 Now playing: {song_name}")
    print(f"📁 Playlist: {playlist_name}")
    print(f"⏯️ Status: {status}")
    print(f"🔁 Loop: {loop_mode.capitalize()}\n")

    print("What do you want to loop?")
    print("[S] Song | [P] Playlist | [N] No loop | [B] Back")
    print("> ", end="", flush=True)

def command_listener(start_event, paused_event, stop_event, state):
    start_event.wait()

    loop_menu = False

    while not stop_event.is_set():
        if os.name == 'nt':  # Windows
            import msvcrt
            if msvcrt.kbhit():
                command = msvcrt.getch().decode('utf-8').upper()
            else:
                time.sleep(0.1)
                continue
        else:  # Linux
            if select.select([sys.stdin], [], [], 0.1)[0]:
                command = sys.stdin.readline().strip().upper()
            else:
                continue

        if stop_event.is_set():
            break

        if loop_menu:
            if command == "S":
                state["loop"] = "song"
                loop_menu = False

            elif command == "P":
                state["loop"] = "playlist"
                loop_menu = False

            elif command == "N":
                state["loop"] = "none"
                loop_menu = False

            elif command == "B":
                loop_menu = False

            else:
                print(colorama.Fore.RED + "Invalid command" + colorama.Fore.GREEN)
                time.sleep(1.5)

            if not stop_event.is_set() and not loop_menu:
                status = colorama.Fore.YELLOW + "Paused" + colorama.Fore.GREEN if paused_event.is_set() else "Playing"

                render_player_ui(state["current_song"], state["playlist_name"], status, state["loop"])

            continue

        if command == "P":
            pygame.mixer.music.pause()
            print(colorama.Fore.YELLOW + "Paused\n" + colorama.Fore.GREEN)

            paused_event.set()
            render_player_ui(state["current_song"], state["playlist_name"], colorama.Fore.YELLOW + "Paused" + colorama.Fore.GREEN, state["loop"])
        elif command == "R":
            pygame.mixer.music.unpause()
            print(colorama.Fore.YELLOW + "Resumed\n" + colorama.Fore.GREEN)

            paused_event.clear()
            render_player_ui(state["current_song"], state["playlist_name"], "Playing", state["loop"])
        elif command == "N":
            pygame.mixer.music.unpause()
            paused_event.clear()

            pygame.mixer.music.stop()
            state["action"] = "next"

        elif command == "B":
            pygame.mixer.music.unpause()
            paused_event.clear()

            pygame.mixer.music.stop()
            state["action"] = "prev"

        elif command == "L":
            loop_menu = True

            if paused_event.is_set():
                render_loop_menu(state["current_song"], state["playlist_name"], colorama.Fore.YELLOW + "Paused" + colorama.Fore.GREEN, state["loop"])
            else:
                render_loop_menu(state["current_song"], state["playlist_name"], "Playing", state["loop"])

        elif command == "S":
            pygame.mixer.music.stop()
            stop_event.set()
            break
        else:
            if not stop_event.is_set() and command:
                print(colorama.Fore.RED + "Invalid command" + colorama.Fore.GREEN)
                time.sleep(1.5)

def play(folder, mp3_files, start_index, state):
    start_event = threading.Event()

    paused_event = threading.Event()
    paused_event.clear()

    stop_event = threading.Event()

    listener = threading.Thread(
        target=command_listener,
        args=(start_event, paused_event, stop_event, state),
        daemon=True
    )
    listener.start()

    state["index"] = start_index

    start_cava()

    try:
        while True:
            i = state["index"]

            if i < 0 or i >= len(mp3_files):
                stop_event.set()
                return

            song = mp3_files[i]
            path = os.path.join(folder, song)

            pygame.mixer.music.load(path)
            pygame.mixer.music.play()

            state["current_song"] = song

            status = colorama.Fore.YELLOW + "Paused" + colorama.Fore.GREEN if paused_event.is_set() else "Playing"

            render_player_ui(song, state["playlist_name"], status, state["loop"])

            start_event.set()

            while True:
                if stop_event.is_set():
                    pygame.mixer.music.stop()
                    return

                if paused_event.is_set():
                    time.sleep(0.2)
                    continue

                if state["action"] in ["prev", "next", "stop"]:
                    pygame.mixer.music.stop()
                    break

                if(not paused_event.is_set() and not pygame.mixer.music.get_busy()):
                    if state["loop"] == "song":
                        state["action"] = "repeat"
                    else:
                        state["action"] = "next"

                    break

                time.sleep(0.3)

            if stop_event.is_set():
                return

            if state["action"] == "repeat":
                pass

            elif state["action"] == "next":
                if state["index"] >= len(mp3_files) - 1:
                    if state["loop"] == "playlist":
                        state["index"] = 0
                    else:
                        stop_event.set()
                        return

                else:
                    state["index"] += 1

            elif state["action"] == "prev":
                if state["index"] > 0:
                    state["index"] -= 1
                else:
                    state["index"] = len(mp3_files) - 1

            elif state["action"] == "stop":
                stop_event.set()
                return

            state["action"] = None

    finally:
        pygame.mixer.music.stop()
        stop_cava()

def select_playlist():
    playlists_folder = "playlists"

    if not os.path.isdir(playlists_folder):
        print(f"{colorama.Fore.RED}Folder '{playlists_folder}' not found!")
        print(f"{colorama.Fore.YELLOW}Creating 'playlists' folder...{colorama.Fore.GREEN}")
        os.makedirs(playlists_folder)
        time.sleep(1.5)
        return None

    playlists = [item for item in os.listdir(playlists_folder) 
                 if os.path.isdir(os.path.join(playlists_folder, item))]

    if not playlists:
        print(f"{colorama.Fore.RED}No playlists found in '{playlists_folder}'!")
        print(f"{colorama.Fore.YELLOW}Create folders inside 'playlists' and add .mp3 files{colorama.Fore.GREEN}")
        time.sleep(2)
        return None

    while True:
        clear_terminal()
        print("***** SELECT A PLAYLIST *****\n")

        for index, playlist in enumerate(playlists, start=1):
            playlist_path = os.path.join(playlists_folder, playlist)
            mp3_count = len([f for f in os.listdir(playlist_path) if f.endswith(".mp3")])
            print(f"{index}. {playlist} ({mp3_count} songs)")

        choice_input = input("\nSelect a playlist (or 'Q' to quit): ").strip()

        if choice_input.upper() == "Q":
            return None

        if not choice_input.isdigit():
            print(colorama.Fore.RED + "Enter a valid number" + colorama.Fore.GREEN)
            time.sleep(1.5)
            continue

        choice = int(choice_input) - 1

        if 0 <= choice < len(playlists):
            selected_playlist = playlists[choice]
            return os.path.join(playlists_folder, selected_playlist)
        else:
            print(colorama.Fore.RED + "Invalid choice" + colorama.Fore.GREEN)
            time.sleep(1.5)

def main():
    try:
        pygame.mixer.init()
    except pygame.error as e:
        print("Audio initialization failed! ", e)
        return

    while True:
        folder = select_playlist()

        if folder is None:
            clear_terminal()
            print("Bye!")
            break

        playlist_name = os.path.basename(folder)

        mp3_files = [file for file in os.listdir(folder) if file.endswith(".mp3")]

        if not mp3_files:
            print(colorama.Fore.RED + f"No .mp3 files found in '{playlist_name}'!" + colorama.Fore.GREEN)
            time.sleep(2)
            continue

        while True:
            clear_terminal()
            print(f"***** PLAYLIST: {playlist_name.upper()} *****")
            print("My song list:")

            for index, song in enumerate(mp3_files, start=1):
                print(f"{index}. {song}")

            choice_input = input("\nEnter the song # to play (or 'B' to go back): ")

            if choice_input.upper() == "B":
                break

            if not choice_input.isdigit():
                print(colorama.Fore.RED + "Enter a valid number" + colorama.Fore.GREEN)
                time.sleep(1.5)
                continue

            choice = int(choice_input) - 1

            state = {
                "current_song": None,
                "playlist_name": playlist_name,
                "index": 0,
                "action": None,
                "loop": "none"
            }
            if 0 <= choice < len(mp3_files):
                play(folder, mp3_files, choice, state)
            else:
                print(colorama.Fore.RED + "Invalid choice" + colorama.Fore.GREEN)
                time.sleep(1.5)
                continue

if __name__ == "__main__":
    main()