import json
import os

DB_FILE = "data.json"

class Database:
    def __init__(self):
        self._load()

    def _load(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {
                "downloader_bots": [],
                "userbot_connected": False
            }
            self._save()

    def _save(self):
        with open(DB_FILE, "w") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def add_downloader_bot(self, username: str):
        username = username.lstrip("@")
        for b in self.data["downloader_bots"]:
            if b["username"] == username:
                b["active"] = True
                self._save()
                return
        self.data["downloader_bots"].append({"username": username, "active": True})
        self._save()

    def remove_downloader_bot(self, username: str):
        username = username.lstrip("@")
        self.data["downloader_bots"] = [
            b for b in self.data["downloader_bots"] if b["username"] != username
        ]
        self._save()

    def get_downloader_bots(self):
        return self.data["downloader_bots"]

    def get_active_bot(self):
        for b in self.data["downloader_bots"]:
            if b["active"]:
                return b
        return None

    def set_userbot_status(self, connected: bool):
        self.data["userbot_connected"] = connected
        self._save()

    def get_userbot_status(self) -> bool:
        return self.data.get("userbot_connected", False)
