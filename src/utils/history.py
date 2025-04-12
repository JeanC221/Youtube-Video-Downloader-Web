import json
import os

class DownloadHistory:
    def __init__(self, max_entries=20):
        self.max_entries = max_entries
        self.history_file = os.path.join(os.path.expanduser("~"), ".youtube_downloader_history.json")
        self.history = []
        self.load()
    
    def add(self, entry):
        self.history.insert(0, entry)
        
        # Limitar tamaño
        if len(self.history) > self.max_entries:
            self.history = self.history[:self.max_entries]
        
        self.save()
    
    def clear(self):
        self.history = []
        self.save()
    
    def load(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
        except Exception as e:
            print(f"Error al cargar el historial: {e}")
            self.history = []
    
    def save(self):
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f)
        except Exception as e:
            print(f"Error al guardar el historial: {e}")