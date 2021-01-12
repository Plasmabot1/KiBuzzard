import os
import sys
import subprocess
import threading
import time

import wx
import wx.aui
from wx import FileConfig

import pcbnew
from .dialog.dialog import Dialog

def check_for_bom_button():
    # From Miles McCoo's blog
    # https://kicad.mmccoo.com/2017/03/05/adding-your-own-command-buttons-to-the-pcbnew-gui/
    def find_pcbnew_window():
        windows = wx.GetTopLevelWindows()
        pcbneww = [w for w in windows if "pcbnew" in w.GetTitle().lower()]
        if len(pcbneww) != 1:
            return None
        return pcbneww[0]

    def callback(_):
        plugin.Run()

    path = os.path.dirname(__file__)
    while not wx.GetApp():
        time.sleep(1)
    bm = wx.Bitmap(path + '/icon.png', wx.BITMAP_TYPE_PNG)
    button_wx_item_id = 0

    from pcbnew import ID_H_TOOLBAR
    while True:
        time.sleep(1)
        pcbnew_window = find_pcbnew_window()
        if not pcbnew_window:
            continue

        top_tb = pcbnew_window.FindWindowById(ID_H_TOOLBAR)
        if button_wx_item_id == 0 or not top_tb.FindTool(button_wx_item_id):
            top_tb.AddSeparator()
            button_wx_item_id = wx.NewId()
            top_tb.AddTool(button_wx_item_id, "KiBuzzard", bm,
                           "Execute Buzzard script", wx.ITEM_NORMAL)
            top_tb.Bind(wx.EVT_TOOL, callback, id=button_wx_item_id)
            top_tb.Realize()

class KiBuzzardPlugin(pcbnew.ActionPlugin, object):
    config_file = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    buzzard_path = os.path.join(os.path.dirname(__file__), '..', 'deps', 'buzzard')

    def __init__(self):
        super(KiBuzzardPlugin, self).__init__()
        self.name = "Create Labels"
        self.category = "Modify PCB"
        self.pcbnew_icon_support = hasattr(self, "show_toolbar_button")
        self.show_toolbar_button = True
        icon_dir = os.path.dirname(os.path.dirname(__file__))
        self.icon_file_name = os.path.join(icon_dir, 'icon.png')
        self.description = "Create Labels"

        self.last_str = ""
        self.load_from_ini()


    def defaults(self):
        pass

    def load_from_ini(self):
        """Init from config file if it exists."""
        if not os.path.isfile(self.config_file):
            return
        f = FileConfig(localFilename=self.config_file)
        f.SetPath('/general')
        self.output_dest_dir = f.Read('last_str', self.last_str)


    def save(self):
        f = FileConfig(localFilename=self.config_file)
        f.SetPath('/general')
        f.Write('last_str', self.last_str)
        f.Flush()


    def Run(self):
        board = pcbnew.GetBoard()
        pcb_file_name = board.GetFileName()

        buzzard_script = os.path.join(self.buzzard_path, 'buzzard.py')
        buzzard_output = os.path.join(self.buzzard_path, 'output.scr')

        
        _pcbnew_frame = [x for x in wx.GetTopLevelWindows() if 'pcbnew' in x.GetTitle().lower() and not 'python' in x.GetTitle().lower()][0]
        dlg = Dialog(_pcbnew_frame, self.last_str)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                import re
                args = [a.strip('"') for a in re.findall('".+?"|\S+', dlg.GetValue())]
                subprocess.run(['python', buzzard_script, *args])

                txt = open(buzzard_output).read()

                pcb_io = pcbnew.PCB_IO()
                footprint = pcbnew.Cast_to_FOOTPRINT(pcb_io.Parse(txt))

                footprint.SetPosition(pcbnew.wxPoint(pcbnew.FromMM(170),pcbnew.FromMM(115)))
                board.Add(footprint)
                pcbnew.Refresh()
                

                self.last_str = dlg.GetValue()
                self.save()
        finally:
            dlg.Destroy()
            
            

plugin = KiBuzzardPlugin()
plugin.register()

# Add a button the hacky way if plugin button is not supported
# in pcbnew, unless this is linux.
if not plugin.pcbnew_icon_support and not sys.platform.startswith('linux'):
    t = threading.Thread(target=check_for_bom_button)
    t.daemon = True
    t.start()
