#! /usr/bin/env python3

import requests
from pathlib import Path
from datetime import date
from bs4 import BeautifulSoup
from optparse import OptionParser
from colorama import Fore, Back, Style
from time import strftime, localtime, time
from multiprocessing import Lock, Pool, cpu_count

status_color = {
    '+': Fore.GREEN,
    '-': Fore.RED,
    '*': Fore.YELLOW,
    ':': Fore.CYAN,
    ' ': Fore.WHITE
}

def display(status, data, start='', end='\n'):
    print(f"{start}{status_color[status]}[{status}] {Fore.BLUE}[{date.today()} {strftime('%H:%M:%S', localtime())}] {status_color[status]}{Style.BRIGHT}{data}{Fore.RESET}{Style.RESET_ALL}", end=end)

def get_arguments(*args):
    parser = OptionParser()
    for arg in args:
        parser.add_option(arg[0], arg[1], dest=arg[2], help=arg[3])
    return parser.parse_args()[0]

lock = Lock()

def download(downloads):
    for path, link in downloads.items():
        response = requests.get(link)
        with open(path, 'wb') as file:
            file.write(response.content)
        with lock:
            display('+', f"Downloaded => {Back.MAGENTA}{path}{Back.RESET}")

if __name__ == "__main__":
    data = get_arguments(('-w', "--write", "write", "Name of the Folder for the data to be dumped (default=current data and time)"),)
    if not data.write:
        data.write = f"{date.today()} {strftime('%H_%M_%S', localtime())}"
    cwd = Path.cwd()
    folder = cwd / data.write
    folder.mkdir(exist_ok=True)
    torrent_folder = folder / "weakpass_torrents"
    torrent_folder.mkdir(exist_ok=True, parents=True)
    link = "https://weakpass.com/wordlist?page=1"
    wordlists = []
    t1 = time()
    while link != '#':
        response = requests.get(link)
        html = BeautifulSoup(response.content, "html.parser")
        link = html.find("a", attrs={"class": "pagination-next"}).get_attribute_list("href")[0]
        wordlist_tags = html.find_all("div", attrs={"class": "card"})
        if len(wordlist_tags) == 0:
            break
        for wordlist_tag in wordlist_tags:
            wordlist = {}
            wordlist["name"] = wordlist_tag.find_all("a")[0].text
            wordlist_tag_text = wordlist_tag.text.split('\n')
            try:
                while True:
                    wordlist_tag_text.remove('')
            except:
                pass
            wordlist["size"] = wordlist_tag_text[2]
            wordlist["uncompressed_size"] = wordlist_tag_text[3]
            wordlist["words"] = int(wordlist_tag_text[4])
            wordlist["torrent_link"] = wordlist_tag.find_all("a")[-1].get_attribute_list("href")[-1]
            wordlists.append(wordlist)
        display('*', f"Wordlists Scrapped = {Back.MAGENTA}{len(wordlists)}{Back.RESET}", start='\r', end='')
    t2 = time()
    display('+', f"\tTime Taken = {Back.MAGENTA}{t2-t1:.2f} seconds{Back.RESET}", start='\n')
    display('+', f"\tRate       = {Back.MAGENTA}{len(wordlists)/(t2-t1):.2f} wordlists/second{Back.RESET}")
    display(':', f"Sorting by Number of Words in Wordlist")
    size_wise_wordlist = {}
    for wordlist in wordlists:
        if wordlist["words"] not in size_wise_wordlist.keys():
            size_wise_wordlist[wordlist["words"]] = []
        size_wise_wordlist[wordlist["words"]].append(wordlist)
    sizes = list(size_wise_wordlist.keys())
    sizes.sort()
    sizes.reverse()
    wordlists = []
    for size in sizes:
        for wordlist in size_wise_wordlist[size]:
            wordlists.append(wordlist)
    display(':', f"Dumping Data to Folder {Back.MAGENTA}{data.write}{Back.RESET}")
    with open(f"{data.write}/weakpass.csv", 'w') as file:
        file.write("Name,Words,Size,Uncompressed Size\n")
        file.write('\n'.join([f"{wordlist['name']},{wordlist['words']},{wordlist['size']},{wordlist['uncompressed_size']}" for wordlist in wordlists]))
    display(':', f"Downloading Torrent Files")
    t1 = time()
    thread_count = cpu_count()
    display(':', f"Creating {Back.MAGENTA}{thread_count} Downloading Threads{Back.RESET}")
    pool = Pool(thread_count)
    downloads = {f"{data.write}/weakpass_torrents/{wordlist['torrent_link'].split('/')[-1]}": wordlist["torrent_link"] for wordlist in wordlists}
    download_paths = list(downloads.keys())
    total_downloads = len(downloads)
    downloads_division = [download_paths[group*total_downloads//thread_count: (group+1)*total_downloads//thread_count] for group in range(thread_count)]
    threads = []
    for download_division in downloads_division:
        threads.append(pool.apply_async(download, ({path:downloads[path] for path in download_division}, )))
    for thread in threads:
        thread.get()
    pool.close()
    pool.join()
    t2 = time()
    display('+', f"\tTime Taken = {Back.MAGENTA}{t2-t1:.2f} seconds{Back.RESET}", start='\n')
    display('+', f"\tRate       = {Back.MAGENTA}{len(wordlists)/(t2-t1):.2f} torrents/second{Back.RESET}")