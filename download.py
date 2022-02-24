import glob
from concurrent.futures import ThreadPoolExecutor
import m3u8
import os
import requests
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES
import requests
import logging

logging.basicConfig(filename="download.log",
                    format='%(asctime)s %(levelname)-10s %(funcName)-20s %(message)s',
                    filemode='a')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
}

MAX_RETRIES = 10

def request_with_retry(url, headers=None, **kwargs):
    for i in range(MAX_RETRIES):
        try:
            data = requests.get(url, headers=headers, **kwargs)
            if (data.ok):
                return data
            else:
                logger.warning(f"Request to URL [{url}] failed. Status code [{data.status_code}]. Retry [{i}]")
                continue
        except Exception as e:
            logger.warning(f"Request to URL [{url}] failed. Retry [{i}]")
            continue
    
    logger.error(f"Request to URL [{url}] failed after {MAX_RETRIES} retries")
    return None

def download_ts(url, key, i, iv):
    r = request_with_retry(url, headers=headers)
    #print("index", i, "got.")
    data = r.content
    #print("Content", i)
    data = AESDecrypt(data, key=bytes.fromhex(key),iv=bytes.fromhex(iv[2:]))
    #print("Decrypted", i)
    with open(f"tmp/{i:0>5d}.ts", "ab") as f:
        f.write(data)
    print(f"\r{i:0>5d}.ts Downloaded", end="  ")


def m3u8_retry_load(uri, headers=None, **kwargs):
    for i in range(MAX_RETRIES):
        try:
            return m3u8.load(uri=uri, headers=headers)
        except Exception as e:
            logger.warning(f"M3U8 Request to URL [{uri}] failed. Retry [{i}]")
            continue
    
    logger.error(f"M3U8 Request to URL [{uri}] failed after {MAX_RETRIES} retries")
    return None


def get_real_url(url):
    playlist = m3u8_retry_load(uri=url, headers=headers)
    return playlist.playlists[1].absolute_uri


def AESDecrypt(cipher_text, key, iv):
    cipher_text = pad(data_to_pad=cipher_text, block_size=AES.block_size)
    aes = AES.new(key=key, mode=AES.MODE_CBC, iv=iv)
    cipher_text = aes.decrypt(cipher_text)
    return cipher_text


def download_m3u8_video(url, save_name, key, max_workers=10):
    if not os.path.exists("tmp"):
        os.mkdir('tmp')

    real_url = get_real_url(url)
    playlist = m3u8_retry_load(uri=real_url, headers=headers)
    logger.debug(f"Playlist loaded for URL [{url}]")
    #print(playlist.keys[0].iv)
    #key = requests.get(playlist.keys[-1].uri, headers=headers).content
    #print("key loaded =", key)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for i, seg in enumerate(playlist.segments):
            logger.debug(f"Downloading segment {i} with URL {seg.absolute_uri}")
            pool.submit(download_ts, seg.absolute_uri, key, i, playlist.keys[i].iv)
            #download_ts(seg.absolute_uri, key, i, playlist.keys[i].iv)

    with open(save_name, 'wb') as fw:
        files = glob.glob('tmp/*.ts')
        files = sorted(files)
        for file in files:
            with open(file, 'rb') as fr:
                fw.write(fr.read())
                print(f'\r{file}Merged!Total:{len(files)}', end="     ")
            os.remove(file)

    logger.info(f"File [{save_name}] downloaded!")

def main():
    # Read csv file contenders.csv
    csv = open("contenders_decoded.csv", "r")
    for line in range(csv.length):
        line = csv[line].strip()
        # TODO This is wrong - use a proper csv parser
        row = csv[line].split(",")
        url = row[1]
        file_name = row[0]
        key = row[8]
        download_m3u8_video(url, file_name.strip() + ".ts", key)

# download_m3u8_video('https://d272f79eqy1rdf.cloudfront.net/6aca9ee8-5af3-4b5d-b490-710058f50f69/master.m3u8','test2.ts', '3c3384493b6a93197f2254248070f459')

