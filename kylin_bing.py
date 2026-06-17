#!/usr/bin/python
# -*- coding: utf-8 -*-
import locale
import os
import re
import sys
import random
import subprocess

# ================== 配置区域 ==================
BASE_DIR = "/home/greatwall/图片/BingWallpapers"
os.makedirs(BASE_DIR, exist_ok=True)

LOG_FILE = os.path.join(BASE_DIR, "image-details.txt")
ICON_PATH = os.path.abspath("icon.svg") if os.path.exists("icon.svg") else ""
DIR_MAX_SIZE = 100 * 1024 * 1024
# ==============================================

os.system("sleep 5")

# --- Python 2/3 兼容 ---
try:
    from urllib.request import urlopen, urlretrieve
except ImportError:
    from urllib2 import urlopen
    from urllib import urlretrieve

import xml.etree.ElementTree as ET
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, Notify

BING_MARKETS = [ ... ]  # 此处省略，与之前相同，请自行保留完整列表

def get_file_uri(filename):
    return 'file://%s' % filename

def set_wallpaper(filename):
    file_uri = get_file_uri(filename)
    # UKUI
    try:
        cmd = ['gsettings', 'set', 'org.ukui.background', 'picture-uri', file_uri]
        if subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            print("成功通过 UKUI 设置壁纸")
            return True
    except: pass
    # MATE
    try:
        cmd = ['gsettings', 'set', 'org.mate.background', 'picture-filename', filename]
        if subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            print("成功通过 MATE 设置壁纸")
            return True
    except: pass
    # GNOME
    try:
        cmd = ['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', file_uri]
        if subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            print("成功通过 GNOME 设置壁纸")
            return True
    except: pass
    print("未能匹配到有效的桌面环境配置，壁纸设置失败")
    return False

def change_screensaver(filename):
    try:
        cmd = ['gsettings', 'set', 'org.ukui.screensaver', 'background', filename]
        subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    try:
        cmd = ['gsettings', 'set', 'org.gnome.desktop.screensaver', 'picture-uri', get_file_uri(filename)]
        subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

def get_market():
    try:
        default_locale = locale.getdefaultlocale()[0]
        if default_locale in BING_MARKETS:
            return default_locale
    except: pass
    return 'zh-CN'

def get_bing_xml():
    market = get_market()
    return "https://www.bing.com/HPImageArchive.aspx?format=xml&idx=0&n=1&mkt=%s" % market

def get_screen_resolution_str():
    """
    获取屏幕分辨率，优先使用 xrandr，避免 Gtk 初始化崩溃。
    如果无法获取，返回默认 1920x1080。
    """
    # 方法1：检查 DISPLAY 环境变量，若没有则直接返回默认
    if not os.environ.get('DISPLAY'):
        print("未检测到 DISPLAY 环境变量，使用默认分辨率 1920x1080")
        return '1920x1080'

    # 方法2：使用 xrandr 获取当前分辨率
    try:
        output = subprocess.check_output(['xrandr', '--current'], stderr=subprocess.DEVNULL, universal_newlines=True)
        # 查找主显示器（primary）或第一个连接的分辨率
        for line in output.splitlines():
            if ' connected' in line and '*' in line:
                # 示例行：*1920x1080     60.00*
                match = re.search(r'(\d+)x(\d+)', line)
                if match:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    # 匹配预定义尺寸（保持与原逻辑一致的缩放）
                    sizes = [
                        [800, [600]], [1024, [768]], [1280, [720, 768]], [1366, [768]],
                        [1920, [1080, 1200]], [2560, [1440]], [3840, [2160]]
                    ]
                    for w_list in sizes:
                        if width <= w_list[0]:
                            width_res = w_list[0]
                            height_list = w_list[1]
                            height_res = height_list[-1]
                            for h in height_list:
                                if height <= h:
                                    height_res = h
                                    break
                            return '%sx%s' % (width_res, height_res)
                    # 未匹配到预定义尺寸，直接返回原始宽高
                    return '%sx%s' % (width, height)
    except Exception as e:
        print("xrandr 获取分辨率失败: %s" % e)

    # 方法3：尝试旧的 Gtk 方法（只作为最后手段）
    try:
        window = Gtk.Window(type=Gtk.WindowType.POPUP)
        screen = window.get_screen()
        width = screen.get_width()
        height = screen.get_height()
        window.destroy()
        sizes = [ ... ]  # 同上匹配逻辑（代码略，与上面一致）
        # 为简洁，直接返回宽高字符串
        return '%sx%s' % (width, height)
    except Exception as e:
        print("Gtk 获取分辨率也失败: %s" % e)

    # 最终回退
    return '1920x1080'

def get_image_metadata():
    bing_xml_url = get_bing_xml()
    try:
        page = urlopen(bing_xml_url)
        bing_xml = ET.parse(page).getroot()
        images = bing_xml.findall('image')
        if images:
            return images[0]
    except Exception as e:
        raise Exception("无法获取 Bing XML 数据: %s" % e)

def get_image_url(metadata):
    base_image = metadata.find("url").text
    screen_size = get_screen_resolution_str()
    correct_resolution_image = re.sub(r'\d+x\d+', screen_size, base_image)
    return "https://www.bing.com" + correct_resolution_image

def p2_dirscan(path):
    files = []
    size = 0
    for e in os.listdir(path):
        entry_path = os.path.join(path, e)
        if os.path.isfile(entry_path) and os.path.splitext(entry_path)[1].lower() == ".jpg":
            s = os.path.getsize(entry_path)
            files.append(entry_path)
            size += s
    return files, size

def check_limit():
    max_size = DIR_MAX_SIZE
    if max_size <= 0:
        return
    files, size = p2_dirscan(BASE_DIR)
    files.sort()
    while size > max_size and len(files) > 1:
        file_to_remove = files[0]
        try:
            file_size = os.path.getsize(file_to_remove)
            os.remove(file_to_remove)
            size -= file_size
            print("已清理旧文件: %s" % file_to_remove)
        except:
            break
        del files[0]

def get_comment_from_log(image_filename):
    if not os.path.isfile(LOG_FILE):
        return None
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(" -- ")
                if len(parts) >= 2 and parts[0] == image_filename:
                    return parts[1]
    except Exception as e:
        print("读取日志文件失败: %s" % e)
    return None

def show_notification(summary, body, timeout_ms=5000):
    Notify.init("Bing Wallpaper")
    try:
        notification = Notify.Notification.new(summary, body, ICON_PATH)
        notification.set_timeout(timeout_ms)
        notification.show()
    except Exception as e:
        print("通知显示失败: %s" % e)

def set_random_wallpaper_from_dir():
    files, _ = p2_dirscan(BASE_DIR)
    if not files:
        return None, None, "文件夹内没有图片"
    chosen = random.choice(files)
    filename = os.path.basename(chosen)
    if set_wallpaper(chosen):
        change_screensaver(chosen)
        comment = get_comment_from_log(filename)
        if not comment:
            comment = filename
        return filename, comment, "随机切换成功"
    else:
        return filename, None, "壁纸设置失败"

def main():
    Notify.init("Bing Wallpaper")
    try:
        image_metadata = get_image_metadata()
        today_name = image_metadata.find("startdate").text + ".jpg"
        copyright_text = image_metadata.find("copyright").text or "未知版权信息"
        image_url = get_image_url(image_metadata)
        today_path = os.path.join(BASE_DIR, today_name)

        if os.path.isfile(today_path):
            print("今日图片已存在: %s，转为随机模式" % today_name)
            filename, comment, result_msg = set_random_wallpaper_from_dir()
            if filename is None:
                print("文件夹为空，强制使用当日图片")
                if not os.path.isfile(today_path):
                    urlretrieve(image_url, today_path)
                set_wallpaper(today_path)
                change_screensaver(today_path)
                comment = copyright_text
                filename = today_name
                result_msg = "文件夹为空，使用当日图片"
            show_notification("壁纸已更换", comment, 5000)
            with open(LOG_FILE, "a", encoding='utf-8') as myfile:
                myfile.write("%s -- %s -- 随机切换 -- %s\n" % (filename, comment, result_msg))
        else:
            print("正在下载新图: %s" % image_url)
            urlretrieve(image_url, today_path)
            set_ok = set_wallpaper(today_path)
            if set_ok:
                change_screensaver(today_path)
                set_result = "成功"
            else:
                set_result = "壁纸设置失败"
            log_line = "%s -- %s -- 下载新图 -- %s\n" % (today_name, copyright_text, set_result)
            with open(LOG_FILE, "a", encoding='utf-8') as myfile:
                myfile.write(log_line)
            show_notification("Bing 今日壁纸", copyright_text, 5000)
            print("壁纸设置完成：%s" % today_name)

        check_limit()
    except Exception as err:
        summary = '壁纸更新失败'
        body = str(err)
        print("错误: %s" % body)
        show_notification(summary, body, 5000)
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()
