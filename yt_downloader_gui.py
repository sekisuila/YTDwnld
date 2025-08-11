import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from pytubefix import YouTube, Playlist, Channel, Search
except Exception as e:
    YouTube = Playlist = Channel = Search = None
    print("pytubefix is not available:", e)

class YTDownloaderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("1000x700")
        self.download_dir = os.getcwd()
        self.url_map = {}
        self.create_widgets()

    def create_widgets(self):
        path_frame = ttk.Frame(self)
        path_frame.pack(fill=tk.X, pady=5)
        ttk.Label(path_frame, text="Download folder:").pack(side=tk.LEFT, padx=5)
        self.path_var = tk.StringVar(value=self.download_dir)
        ttk.Entry(path_frame, textvariable=self.path_var, width=60).pack(side=tk.LEFT, padx=5)
        ttk.Button(path_frame, text="Choose", command=self.choose_folder).pack(side=tk.LEFT)

        mode_frame = ttk.LabelFrame(self, text="Mode")
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        self.mode = tk.StringVar(value="video")
        modes = [
            ("Single video", "video"),
            ("Playlist", "playlist"),
            ("Search", "search"),
            ("Channel list", "channel"),
            ("Download channel", "channel_all"),
        ]
        for txt, val in modes:
            ttk.Radiobutton(mode_frame, text=txt, variable=self.mode, value=val).pack(side=tk.LEFT, padx=5)

        query_frame = ttk.Frame(self)
        query_frame.pack(fill=tk.X, pady=5)
        ttk.Label(query_frame, text="Query / URL:").pack(side=tk.LEFT, padx=5)
        self.query_var = tk.StringVar()
        ttk.Entry(query_frame, textvariable=self.query_var, width=70).pack(side=tk.LEFT, padx=5)
        ttk.Button(query_frame, text="Fetch", command=self.fetch).pack(side=tk.LEFT)

        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.listbox = tk.Listbox(list_frame)
        self.listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.listbox.bind("<Double-Button-1>", self.download_selected)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Download video", command=lambda: self.download_selected(video=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Download audio", command=lambda: self.download_selected(video=False)).pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(self, length=400)
        self.progress.pack(pady=5)

    def choose_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.download_dir = path
            self.path_var.set(path)

    def fetch(self):
        mode = self.mode.get()
        query = self.query_var.get()
        self.listbox.delete(0, tk.END)
        self.url_map.clear()
        if not query:
            return
        if mode == "video" and YouTube:
            yt = YouTube(query)
            idx = self.listbox.size()
            self.listbox.insert(tk.END, f"{yt.title} | {yt.author} | {yt.length}s")
            self.url_map[idx] = yt.watch_url
        elif mode == "playlist" and Playlist:
            pl = Playlist(query)
            for yt in pl.videos:
                idx = self.listbox.size()
                self.listbox.insert(tk.END, yt.title)
                self.url_map[idx] = yt.watch_url
        elif mode == "search" and Search:
            s = Search(query)
            for yt in s.results:
                idx = self.listbox.size()
                self.listbox.insert(tk.END, yt.title)
                self.url_map[idx] = yt.watch_url
        elif mode == "channel" and Channel:
            ch = Channel(query)
            for yt in ch.videos:
                idx = self.listbox.size()
                self.listbox.insert(tk.END, yt.title)
                self.url_map[idx] = yt.watch_url
        elif mode == "channel_all" and Channel:
            ch = Channel(query)
            for yt in ch.videos:
                idx = self.listbox.size()
                self.listbox.insert(tk.END, yt.title)
                self.url_map[idx] = yt.watch_url
            self.download_all([yt.watch_url for yt in ch.videos], video=True)
        else:
            messagebox.showerror("Error", "pytubefix is not available")

    def download_selected(self, event=None, video=True):
        selection = self.listbox.curselection()
        if not selection:
            return
        index = selection[0]
        url = self.url_map.get(index, self.listbox.get(index))
        threading.Thread(target=self.download, args=(url, video)).start()

    def download_all(self, urls, video=True):
        for url in urls:
            self.download(url, video)

    def progress_callback(self, stream, chunk, bytes_remaining):
        total = stream.filesize
        done = total - bytes_remaining
        percent = int(done / total * 100)
        self.progress['value'] = percent
        self.update_idletasks()

    def download(self, url, video=True):
        if not YouTube:
            messagebox.showerror("Error", "pytubefix is not available")
            return
        yt = YouTube(url, on_progress_callback=self.progress_callback)
        title = yt.title
        meta_path = os.path.join(self.download_dir, f"{title}.txt")
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(f"Title: {yt.title}\n")
            f.write(f"Channel: {yt.author}\n")
            f.write(f"Duration: {yt.length}s\n")
            if yt.captions:
                f.write("Subtitles:\n")
                for lang in yt.captions.keys():
                    f.write(f" - {lang}\n")
        if video:
            stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
            out_file = stream.download(output_path=self.download_dir)
        else:
            stream = yt.streams.filter(only_audio=True).first()
            out_file = stream.download(output_path=self.download_dir)
            base, _ = os.path.splitext(out_file)
            os.rename(out_file, base + ".mp3")
        self.progress['value'] = 0
        messagebox.showinfo("Done", f"Downloaded: {title}")

if __name__ == "__main__":
    app = YTDownloaderGUI()
    app.mainloop()
