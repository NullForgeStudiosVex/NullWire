# ==============================
# Imports / Setup
# ==============================
import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import setproctitle
import json
import os
import time


# ==============================
# Safety Check
# ==============================

result = subprocess.check_output(
    ["./NW.sh", "SafteyCheck"]
).decode().strip()

if result == "yes":
    exit()

# ==============================
# System Stuff
# ==============================
setproctitle.setproctitle("NullWire")

def StartTray():
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('AppIndicator3', '0.1')

    from gi.repository import Gtk, AppIndicator3

    iconPath = os.path.join(os.path.dirname(__file__), "NullWire.png")

    indicator = AppIndicator3.Indicator.new(
        "nullwire",
        iconPath,
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS
    )

    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    menu = Gtk.Menu()

    def Toggle(_):
        def DoToggle():
            if Root.state() == "withdrawn":
                Root.deiconify()
                Root.lift()
                Root.focus_force()
            else:
                Root.withdraw()
        Root.after(0, DoToggle)
        Root.after(0, UpdateMenuLabel)

    def QuitApp(_):
        def DoQuit():
            subprocess.run(["./NW.sh", "ClearSinks"])
            subprocess.run(["pkill", "-f", "NullWire.sh"])
            Root.destroy()
            Gtk.main_quit()

        Root.after(0, DoQuit)

    itemQuit = Gtk.MenuItem(label="Quit")
    itemQuit.connect("activate", QuitApp)
    menu.append(itemQuit)

    spacer = Gtk.MenuItem(label="———")
    spacer.set_sensitive(False)
    menu.append(spacer)

    itemToggle = Gtk.MenuItem()
    itemToggle.connect("activate", Toggle)
    menu.append(itemToggle)

    menu.show_all()
    indicator.set_menu(menu)

    def UpdateMenuLabel():
        if Root.state() == "withdrawn":
            itemToggle.set_label("Show")
        else:
            itemToggle.set_label("Hide")

    UpdateMenuLabel()

    def OnMap(_):
        UpdateMenuLabel()

    def OnUnmap(_):
        UpdateMenuLabel()

    Root.bind("<Map>", OnMap)
    Root.bind("<Unmap>", OnUnmap)

    Gtk.main()

# ==============================
# Variables
# ==============================
ConfigPath = "config.json"

Sinks = {}

Devices = {
    "A": {f"A{i}": None for i in range(1, 21)},
    "M": {f"M{i}": None for i in range(1, 21)}
}

OutputDevices = []
InputDevices = []

IgnoreSources = [
    "speech-dispatcher",
    "speech-dispatcher-dummy",
]

# ==============================
# Saving / Loading
# ==============================
def SaveConfig():
    with open(ConfigPath, "w") as f:
        json.dump({
            "Sinks": Sinks,
            "Devices": Devices
        }, f, indent=4)

def LoadConfig():
    global Sinks, Devices

    if not os.path.exists(ConfigPath):
        data = {
            "Sinks": {},
            "Devices": Devices
        }

        with open(ConfigPath, "w") as f:
            json.dump(data, f, indent=4)
    else:
        with open(ConfigPath, "r") as f:
            data = json.load(f)

    Sinks = data.get("Sinks", {})
    Devices = data.get("Devices", Devices)



# ==============================
# Audio Device Scanning
# ==============================
def RefreshOutputDevices():
    global OutputDevices

    try:
        out = subprocess.check_output(["pactl", "list", "sinks"]).decode()
    except:
        OutputDevices = []
        return
    
    used_ids = set()
    for slot in Devices["A"].values():
        if slot and "ID" in slot:
            used_ids.add(slot["ID"])

    devices = []
    current = {}

    for line in out.splitlines():
        line = line.strip()

        if line.startswith("Name:"):
            current["SystemID"] = line.split(":", 1)[1].strip()

        elif line.startswith("Description:"):
            current["UIName"] = line.split(":", 1)[1].strip()

            if "SystemID" in current:
                #if current["SystemID"] not in Sinks:
                if current["SystemID"] not in used_ids:
                    devices.append(current)
                current = {}

    OutputDevices = devices

def RefreshInputDevices():
    global InputDevices

    try:
        out = subprocess.check_output(["pactl", "list", "sources"]).decode()
    except:
        InputDevices = []
        return
    
    used_ids = set()
    for slot in Devices["M"].values():
        if slot and "ID" in slot:
            used_ids.add(slot["ID"])

    devices = []
    current = {}

    for line in out.splitlines():
        line = line.strip()

        if line.startswith("Name:"):
            current["SystemID"] = line.split(":", 1)[1].strip()

        elif line.startswith("Description:"):
            current["UIName"] = line.split(":", 1)[1].strip()

            if "SystemID" in current:
                if ".monitor" not in current["SystemID"] and current["SystemID"] not in used_ids:
                    devices.append(current)
                current = {}

    InputDevices = devices

def GetAudioSources():
    try:
        out = subprocess.check_output(
            ["pactl", "list", "sink-inputs"]
        ).decode()
    except:
        return []

    sources = []

    for line in out.splitlines():
        line = line.strip()

        if "application.name" in line:
            name = line.split("=", 1)[1].strip().strip('"')

            if any(ignore in name for ignore in IgnoreSources):
                continue

            if name not in sources:
                sources.append(name)

    return sources

def GetAudioDeviceVolume(DeviceID):
    try:
        out = subprocess.check_output(
            ["pactl", "get-sink-volume", DeviceID]
        ).decode()

        for part in out.split():
            if "%" in part:
                return int(part.replace("%", ""))
    except:
        pass

    return 0

def GetMicrophoneVolume(source):
    try:
        out = subprocess.check_output(
            ["pactl", "get-source-volume", source]
        ).decode()

        for part in out.split():
            if "%" in part:
                return int(part.replace("%", ""))
    except:
        pass

    return 0

def GetSinkVolume(name):
    try:
        out = subprocess.check_output(
            ["pactl", "get-sink-volume", name]
        ).decode()

        for part in out.split():
            if "%" in part:
                return int(part.replace("%", ""))
    except:
        return None

def ResolveSinkID(name):
    for d in OutputDevices:
        if d["UIName"] == name:
            return d["SystemID"]
    return None

def ResolveSourceID(target_name):
    out = subprocess.check_output(["pactl", "list", "short", "sources"]).decode()

    for line in out.splitlines():
        parts = line.split()
        idx = parts[0]
        name = parts[1]

        if target_name in name:
            return idx

    return None

# ==============================
# UI
# ==============================
Root = tk.Tk()
Root.title("NullWire")
Root.geometry("1600x900")
Root.iconphoto(True, tk.PhotoImage(file="NullWire.png"))

def ToggleWindow(event=None):
    if Root.state() == "withdrawn":
        Root.deiconify()
    else:
        Root.withdraw()
#-----------------------------------------ScrollableWindows
class ScrollableFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.Canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=self.Canvas.yview)

        self.Inner = tk.Frame(self.Canvas)

        # 👇 STORE THIS
        self.Window = self.Canvas.create_window((0, 0), window=self.Inner, anchor="nw")

        self.Inner.bind(
            "<Configure>",
            lambda e: self.Canvas.configure(scrollregion=self.Canvas.bbox("all"))
        )

        # 👇 THIS IS THE FIX
        self.Canvas.bind(
            "<Configure>",
            lambda e: self.Canvas.itemconfig(self.Window, width=e.width)
        )

        self.Canvas.configure(yscrollcommand=scrollbar.set)

        self.Canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

#-----------------------------------------Main
ActiveColor = "darkgray"
InactiveColor = "lightgray"
Main = tk.Frame(Root)
Main.pack(fill="both", expand=True, padx=10, pady= 10)
TabBar = tk.Frame(Main)
TabBar.pack(fill="x")
PageContainer = tk.Frame(Main)
PageContainer.pack(fill="both", expand=True)
RoutingPage = tk.Frame(PageContainer)
DevicesPage = tk.Frame(PageContainer)
for Page in (RoutingPage, DevicesPage):
    Page.place(relwidth=1, relheight=1)

def Show(Page):
    Page.lift()

    # reset all tabs
    RoutingTab.config(bg=InactiveColor)
    DevicesTab.config(bg=InactiveColor)

    # activate correct one
    if Page == RoutingPage:
        RoutingTab.config(bg=ActiveColor)
    elif Page == DevicesPage:
        DevicesTab.config(bg=ActiveColor)

RoutingTab = tk.Button(TabBar, text="Routing")
DevicesTab = tk.Button(TabBar, text="Devices")
RoutingTab.pack(side="left", fill="x", expand=True)
DevicesTab.pack(side="left", fill="both", expand=True)
RoutingTab.config(command=lambda: Show(RoutingPage))
DevicesTab.config(command=lambda: Show(DevicesPage))
Show(RoutingPage)

#-------------------------------- Routing Page
Separator = tk.Frame(RoutingPage, height=2, bg="#555555")
Separator.pack(fill="x", pady=5)
RoutingTop = tk.Frame(RoutingPage)
RoutingTop.pack(fill="x")
RoutingEntry = tk.Entry(RoutingTop)
RoutingEntry.pack(side="left", fill="x", expand=True)
AddButton = tk.Button(RoutingTop, text="Add")
AddButton.pack(side="left", fill="x", expand=True)


ScrollArea = ScrollableFrame(RoutingPage)
ScrollArea.pack(fill="both", expand=True)

RoutingObjects = ScrollArea.Inner

def IsOutputEnabled(Sink, key):
    return Sink["Outputs"].get(key, False)

def IsInputEnabled(Sink, key):
    return Sink["Inputs"].get(key, False)

def AddRoutingObject():
    global Sinks
    name = RoutingEntry.get().strip()
    if not name:
        name = f"Sink {len(Sinks)}"

    new = {
        "Mono": False,
        "Outputs": {f"A{i}": False for i in range(1, 21)},
        "Inputs":  {f"M{i}": False for i in range(1, 21)},
        "Sources": [],
        "Volume": 100,
    }
    

    Sinks[name] = new
    subprocess.run([
            "./NW.sh",
            "CreateSink",
            name
        ])
    SaveConfig()
    RefreshRoutingUI()

    RoutingEntry.delete(0, tk.END)

AddButton.config(command=AddRoutingObject)

def AddRoutingBlock(name, Sink):
    Frame = tk.Frame(RoutingObjects, bd=2, relief="solid")
    Frame.pack(fill="x", padx=5, pady=5)

    # ==============================
    # GRID SETUP
    # ==============================
    Frame.columnconfigure(0, weight=1)  # Button 1
    #Frame.columnconfigure(1, weight=0)  # Button2/Spacer
    #Frame.columnconfigure(2, weight=1)  # InfoField

    Frame.rowconfigure(0, weight=1)  # TOP SECTION
    Frame.rowconfigure(1, weight=1)  # DIVIDER
    Frame.rowconfigure(2, weight=1)  # AUDIO DEVICES
    Frame.rowconfigure(3, weight=1)  # MIC DEVICES
    Frame.rowconfigure(4, weight=1)  # SOUND SOURCES
    Frame.rowconfigure(5, weight=1)  # Spacer

    tk.Frame(Frame, height=5)\
    .grid(row=5, column=0, columnspan=3)

    # ==============================
    # TOP ROW (DELETE + NAME)
    # ==============================
    def Delete():
        del Sinks[name]
        subprocess.run([
        "./NW.sh",
        "DeleteSink",
        name,
        ])

        SaveConfig()
        RefreshRoutingUI()

    Column0 = tk.Frame(Frame)
    Column0.grid(row=0, column=0, sticky="ew", padx=5)

    Column0.columnconfigure(0, weight=0)  # Delete
    Column0.columnconfigure(1, weight=0)  # Mono
    Column0.columnconfigure(2, weight=2)  # label
    Column0.columnconfigure(3, weight=1)  # Volume

    tk.Button(Column0, text="Delete", command=Delete)\
        .grid(row=0, column=0, padx=5, pady=5, sticky="w")
    
    MonoVar = tk.BooleanVar(value=Sink["Mono"])

    

    InnerFrame = tk.Frame(Column0, bd=2, relief="solid")
    InnerFrame.grid(row=0, column=2, sticky="ew", padx=2)

    InnerFrame.columnconfigure(0, weight=1)

    tk.Label(InnerFrame, text=name, anchor="w")\
    .grid(row=0, column=0, sticky="ew")

    volume_frame = tk.Frame(Column0)
    volume_frame.grid(row=0, column=3, sticky="ew", padx=5)
    volume_frame.columnconfigure(0, weight=1)

    start_vol = Sink.get("Volume", 100)
    vol_var = tk.StringVar(value=str(start_vol))

    after_id = None

    def ApplyVolume():
        volumenumber = scale.get()
        Sink["Volume"] = volumenumber
        SaveConfig()

        subprocess.run([
            "./NW.sh",
            "SetSinkVolume",
            name,
            str(volumenumber)
        ])

    def ScheduleApply():
        nonlocal after_id
        if after_id:
            Root.after_cancel(after_id)
        after_id = Root.after(150, ApplyVolume)

    def OnVolumeChange(val):
        vol_var.set(str(int(float(val))))

    scale = tk.Scale(
    volume_frame,
    from_=0,
    to=150,
    orient="horizontal",
    showvalue=0,
    #length=600,
    #sliderlength=10,
    command=OnVolumeChange
    )
    scale.grid(row=0, column=0, sticky="ew")

    scale.bind("<ButtonRelease-1>", lambda e: ApplyVolume())
    scale.bind("<Button-4>", lambda e: (scale.set(min(150, scale.get()+5)), ScheduleApply()))
    scale.bind("<Button-5>", lambda e: (scale.set(max(0, scale.get()-5)), ScheduleApply()))

    scale.set(start_vol)

    tk.Label(volume_frame, textvariable=vol_var, width=3)\
    .grid(row=0, column=1, padx=5)

    # ==============================
    # THICK DIVIDER
    # ==============================
    tk.Frame(Frame, height=3, bg="#555")\
        .grid(row=1, column=0, columnspan=3, sticky="ew", pady=3)
    

    # ==============================
    # AUDIO DEVICES ROW
    # ==============================
    RowA = tk.Frame(Frame)
    RowA.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5)
    RowA.columnconfigure(0, weight=1)

    AllDevices = [f"A{i}" for i in range(1, 21)]

    for i, device in enumerate(AllDevices):
        RowA.columnconfigure(i, weight=1)
        enabled = IsOutputEnabled(Sink, device)
        var = tk.BooleanVar(value=enabled)

        is_active = IsOutputEnabled(Sink, device)
        exists = Devices["A"].get(device) is not None
        

        def Toggle(d=device, v=var):
            DeviceData = Devices["A"].get(d)
            if not DeviceData:
                v.set(False)
                Sink["Outputs"][d] = False
                SaveConfig()
                return
            DeviceID = DeviceData["ID"]

            if v.get():
                subprocess.run([
                    "./NW.sh",
                    "ConnectSinkToAux",
                    name,
                    DeviceID,
                    str(int(Sink["Mono"]))
                ])
                Sink["Outputs"][d] = True
            else:
                subprocess.run([
                    "./NW.sh",
                    "RemoveSinkFromAux",
                    name,
                    DeviceID
                ])
                Sink["Outputs"][d] = False

            SaveConfig()

        cb = tk.Checkbutton(
        RowA,
        text=device,
        variable=var,
        width=3,
        command=Toggle,
        anchor="w"
        )
        cb.grid(row=0, column=i, sticky="ew", padx=2, pady=2)

        if not exists:
            cb.config(state="disabled")

        
    
    # ==============================
    # MIC DEVICES ROW
    # ==============================
    RowM = tk.Frame(Frame)
    RowM.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5)
    RowM.columnconfigure(0, weight=1)

    # ------------------------------
    # BUILD TOGGLES
    # ------------------------------
    AllMics = [f"M{i}" for i in range(1, 21)]

    for i, device in enumerate(AllMics):
        RowM.columnconfigure(i, weight=1)

        is_active = IsInputEnabled(Sink, device)
        var = tk.BooleanVar(value=is_active)

        DeviceData = Devices["M"].get(device)
        exists = DeviceData is not None

        def Toggle(d=device, v=var):
            DeviceID = Devices["M"][d]["ID"]

            if v.get():
                subprocess.run([
                    "./NW.sh",
                    "ConnectMicToSink",
                    DeviceID,
                    name
                ])
                Sink["Inputs"][d] = True
            else:
                subprocess.run([
                    "./NW.sh",
                    "RemoveMicFromSink",
                    DeviceID,
                    name
                ])
                Sink["Inputs"][d] = False
            SaveConfig()

        cb = tk.Checkbutton(
            RowM,
            text=device,
            variable=var,
            width=3,
            command=Toggle,
            anchor="w"
        )
        cb.grid(row=0, column=i, sticky="ew", padx=2, pady=2)

        if not exists:
            cb.config(state="disabled")

    # ==============================
    # SOURCES ROW
    # ==============================
    SRow = tk.Frame(Frame)
    SRow.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5)

    SRow.columnconfigure(2, weight=1)

    tk.Button(SRow, text="Attach", width=6, command=lambda: OpenAddSourcePopup(name, Sink))\
    .grid(row=0, column=0, sticky="ew")

    tk.Button(SRow, text="Remove", width=6, command=lambda: OpenRemoveSourcePopup(Sink))\
    .grid(row=0, column=1, padx=(5,0), sticky="ew")

    InnerFrameS = tk.Frame(SRow, bd=1, relief="solid")
    InnerFrameS.grid(row=0, column=2, sticky="nsew", padx=5)

    InnerFrameS.columnconfigure(0, weight=1)
    InnerFrameS.rowconfigure(0, weight=1)

    tk.Label(
        InnerFrameS,
        text = ", ".join(Sink["Sources"]) if Sink["Sources"] else "",
        anchor="nw",
        justify="left"
    ).grid(row=0, column=0, sticky="nsew")

    # ==============================
    # Mono cause why not
    # ==============================

    def ToggleMono():
        Sink["Mono"] = MonoVar.get()
        for d, enabled in Sink["Outputs"].items():
            if not enabled:
                continue

            DeviceData = Devices["A"].get(d)
            if not DeviceData:
                
                continue

            DeviceID = DeviceData["ID"]

            # disconnect
            subprocess.run([
                "./NW.sh",
                "RemoveSinkFromAux",
                name,
                DeviceID
            ])

            # reconnect with new mono setting
            subprocess.run([
                "./NW.sh",
                "ConnectSinkToAux",
                name,
                DeviceID,
                str(int(Sink["Mono"]))
            ])
        SaveConfig()

    tk.Checkbutton(
        Column0,
        text="Mono?",
        variable=MonoVar,
        command=ToggleMono)\
        .grid(row=0, column=1, padx=5, pady=5, sticky="w")
    



#--- source commands
def OpenAddSourcePopup(name, Sink):
    sources = GetAudioSources()

    if len(sources) == 0:
        return

    Popup = tk.Toplevel(Root)
    Popup.title("Attach Source")
    Popup.geometry("300x400")
    Popup.grab_set()

    for src in sources:
        found = False

        owner = None
        for n, s in Sinks.items():
            if src in s["Sources"]:
                owner = n
                break
        
        bg = "#555555" if owner else None
        fg = "#aaaaaa" if owner else None
        label = src if not owner else f"{src} [FROM: {owner}]"

        tk.Button(
            Popup,
            text=label,
            command=lambda s=src: SelectSource(name, Sink, s, Popup)
        ).pack(fill="x")

def SelectSource(name, Sink, source, Popup):
    for s in Sinks.values():
        if source in s["Sources"]:
            s["Sources"].remove(source)

    Sink["Sources"].append(source)

    subprocess.run([
        "./NW.sh",
        "ConnectSourceToSink",
        source,
        name
    ])

    SaveConfig()
    RefreshRoutingUI()
    Popup.destroy()

def OpenRemoveSourcePopup(Sink):
    if len(Sink["Sources"]) == 0:
        return

    Popup = tk.Toplevel(Root)
    Popup.title("Remove Source")
    Popup.geometry("300x400")
    Popup.grab_set()

    for src in Sink["Sources"]:
        tk.Button(
            Popup,
            text=src,
            command=lambda s=src: RemoveSource(Sink, s, Popup)
        ).pack(fill="x")

def RemoveSource(Sink, source, Popup):
    if source in Sink["Sources"]:
        Sink["Sources"].remove(source)
    subprocess.run([
    "./NW.sh",
    "RemoveSourceFromSink",
    source
    ])
    SaveConfig()
    RefreshRoutingUI()
    Popup.destroy()

def SourceConnection(name,  source):
    subprocess.run([
        "./NW.sh",
        "ConnectSourceToSink",
        source,
        name
    ])

def RefreshRoutingUI():
    for w in RoutingObjects.winfo_children():
        w.destroy()

    for name, sink in Sinks.items():
        AddRoutingBlock(name, sink)





#-------------------------------- Devices Page

Divider = tk.Frame(DevicesPage, height=2, bg="#555")
Divider.pack(fill="x", pady=5)

MainRow = tk.Frame(DevicesPage)
MainRow.pack(fill="both", expand=True)

MainRow.columnconfigure(0, weight=49, uniform="group")
MainRow.columnconfigure(1, weight=2,  uniform="group")
MainRow.columnconfigure(2, weight=49, uniform="group")

# ----- LEFT COLUMN (A) -----
LeftColumn = tk.Frame(MainRow)
LeftColumn.grid(row=0, column=0, sticky="nsew", padx=(5, 2))

# ----- DIVIDER -----
Divider = tk.Frame(MainRow, bg="#555", width=4)
Divider.grid(row=0, column=1, sticky="ns")

# ----- RIGHT COLUMN (M) -----
RightColumn = tk.Frame(MainRow)
RightColumn.grid(row=0, column=2, sticky="nsew", padx=(2, 5))



def CreateABlock(i):
    frame = tk.Frame(LeftColumn, bd=1, relief="solid")
    frame.pack(fill="x", pady=2)

    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=0)
    frame.columnconfigure(2, weight=0)

    AKey = f"A{i}"
    data = Devices["A"][AKey]
    name = data["Name"] if data else "-"

    # clipped label
    container = tk.Frame(frame)
    container.grid(row=0, column=0, sticky="nsew", padx=5)
    container.columnconfigure(0, weight=1)
    container.grid_propagate(False)

    tk.Label(container, text=f"{AKey}: {name}", anchor="w")\
        .grid(row=0, column=0, sticky="w")
    
    volume = tk.Frame(frame)
    volume.grid(row=0, column=1, sticky="e", padx=5)

    volume_controls = tk.Frame(volume)
    volume_controls.grid(row=0, column=0)

    device_id = data["ID"] if data else None
    start_vol = data.get("Volume") if data else None

    if start_vol is None:
        start_vol = GetAudioDeviceVolume(device_id) if device_id else 100

    vol_var = tk.StringVar(value=str(start_vol))

    after_id = None

    def ApplyVolume(data):
        if not data:
            return

        volumenumber = data.get("Volume", 100)

        device_id = data.get("ID")

        # 🔥 try to resolve if missing
        if not device_id:
            device_id = ResolveSinkID(data["Name"])

        if not device_id:
            return

        data["ID"] = device_id

        try:
            subprocess.run([
                "pactl",
                "set-sink-volume",
                device_id,
                f"{volumenumber}%"
            ], check=True)

        except subprocess.CalledProcessError:
            # 🔥 ID probably changed → re-resolve
            new_id = ResolveSinkID(data["Name"])

            if not new_id:
                return

            data["ID"] = new_id
            SaveConfig()

            subprocess.run([
                "pactl",
                "set-sink-volume",
                new_id,
                f"{volumenumber}%"
            ], check=True)

    def ScheduleApply():
        nonlocal after_id

        if after_id:
            Root.after_cancel(after_id)

        after_id = Root.after(150, ApplyVolume)

    def OnVolumeChange(val):
        volumenumber = int(float(val))
        vol_var.set(str(volumenumber))

    scale = tk.Scale(
        volume_controls,
        from_=0,
        to=150,
        orient="horizontal",
        showvalue=0,
        length=120,
        sliderlength=10,
        command=OnVolumeChange
    )
    scale.grid(row=0, column=0, sticky="e", padx=5)

    def OnScrollUp(event):
        scale.set(min(150, scale.get() + 5))
        OnVolumeChange(scale.get())
        ScheduleApply()

    def OnScrollDown(event):
        scale.set(max(0, scale.get() - 5))
        OnVolumeChange(scale.get())
        ScheduleApply()

    scale.bind("<ButtonRelease-1>", lambda e: ApplyVolume())
    scale.bind("<Button-4>", OnScrollUp)
    scale.bind("<Button-5>", OnScrollDown)

    scale.set(start_vol)

    override_var = tk.BooleanVar(value=data.get("Dominant", False) if data else False)

    def ToggleOverride():
        state = override_var.get()

        data["Dominant"] = state
        SaveConfig()
        if state:
            volume_controls.grid()
        else:
            volume_controls.grid_remove()

    tk.Label(volume_controls, textvariable=vol_var, anchor="w", width= 3)\
        .grid(row=0, column=1, sticky="w")

    tk.Checkbutton(
            volume,
            text="Override System",
            width = 15,
            variable=override_var,
            command=ToggleOverride,
            anchor="w"
        ).grid(row=0, column=2, sticky="e", padx=1, pady=2)
    
    if override_var.get():
        volume_controls.grid()
    else:
        volume_controls.grid_remove()


    # buttons
    btns = tk.Frame(frame)
    btns.grid(row=0, column=2)

    tk.Button(btns, text="SET",
        command=lambda k=AKey: OpenOutputPopup(k)).pack(side="left")

    tk.Button(btns, text="CLEAR",
        command=lambda k=AKey: ClearOutput(k)).pack(side="left")
    
def CreateMBlock(i):
    frame = tk.Frame(RightColumn, bd=1, relief="solid")
    frame.pack(fill="x", pady=2)

    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=0)
    frame.columnconfigure(2, weight=0)

    MKey = f"M{i}"
    data = Devices["M"][MKey]
    name = data["Name"] if data else "-"

    # label
    container = tk.Frame(frame)
    container.grid(row=0, column=0, sticky="nsew", padx=5)
    container.columnconfigure(0, weight=1)
    container.grid_propagate(False)

    tk.Label(container, text=f"{MKey}: {name}", anchor="w")\
        .grid(row=0, column=0, sticky="w")

    volume = tk.Frame(frame)
    volume.grid(row=0, column=1, sticky="e", padx=5)

    volume_controls = tk.Frame(volume)
    volume_controls.grid(row=0, column=0)

    device_id = data["ID"] if data else None
    start_vol = data.get("Volume") if data else None

    if start_vol is None:
        start_vol = GetMicrophoneVolume(device_id) if device_id else 100

    vol_var = tk.StringVar(value=str(start_vol))

    after_id = None

    def ApplyVolume():
        if not data:
            return

        volumenumber = scale.get()
        data["Volume"] = volumenumber
        SaveConfig()

        device_id = data.get("ID")

        if not device_id:
            device_id = ResolveSourceID(data["Name"])
        
        if not device_id:
            return
        
        data["ID"] = device_id

        try:
            subprocess.run([
                "pactl",
                "set-source-volume",
                device_id,
                f"{volumenumber}%"
            ], check=True)

        except subprocess.CalledProcessError:
            new_id = ResolveSourceID(data["Name"])

            if not new_id:
                return

            data["ID"] = new_id
            SaveConfig()

            subprocess.run([
                "pactl",
                "set-source-volume",
                new_id,
                f"{volumenumber}%"
            ], check=True)

    def ScheduleApply():
        nonlocal after_id
        if after_id:
            Root.after_cancel(after_id)
        after_id = Root.after(150, ApplyVolume)

    def OnVolumeChange(val):
        volumenumber = int(float(val))
        vol_var.set(str(volumenumber))

    scale = tk.Scale(
        volume_controls,
        from_=0,
        to=150,
        orient="horizontal",
        showvalue=0,
        length=120,
        sliderlength=10,
        command=OnVolumeChange
    )
    scale.grid(row=0, column=0, sticky="e", padx=5)

    def OnScrollUp(event):
        scale.set(min(150, scale.get() + 5))
        OnVolumeChange(scale.get())
        ScheduleApply()

    def OnScrollDown(event):
        scale.set(max(0, scale.get() - 5))
        OnVolumeChange(scale.get())
        ScheduleApply()

    scale.bind("<ButtonRelease-1>", lambda e: ApplyVolume())
    scale.bind("<Button-4>", OnScrollUp)
    scale.bind("<Button-5>", OnScrollDown)

    scale.set(start_vol)

    override_var = tk.BooleanVar(value=data.get("Dominant", False) if data else False)

    def ToggleOverride():
        if not data:
            return

        state = override_var.get()
        data["Dominant"] = state
        SaveConfig()

        if state:
            volume_controls.grid()
        else:
            volume_controls.grid_remove()

    tk.Label(volume_controls, textvariable=vol_var, width=3)\
        .grid(row=0, column=1, sticky="w")

    tk.Checkbutton(
        volume,
        text="Override System",
        width=15,
        variable=override_var,
        command=ToggleOverride,
        anchor="w"
    ).grid(row=0, column=2, sticky="e", padx=1, pady=2)

    if override_var.get():
        volume_controls.grid()
    else:
        volume_controls.grid_remove()

    # buttons
    btns = tk.Frame(frame)
    btns.grid(row=0, column=2)

    tk.Button(btns, text="SET",
        command=lambda k=MKey: OpenInputPopup(k)).pack(side="left")

    tk.Button(btns, text="CLEAR",
        command=lambda k=MKey: ClearInput(k)).pack(side="left")
    

def BuildUI():
    for i in range(1, 21):
        CreateABlock(i)
        CreateMBlock(i)

def RebuildUI():
    global LeftColumn, RightColumn, Divider
    for widget in MainRow.winfo_children():
        widget.destroy()
    LeftColumn = tk.Frame(MainRow)
    LeftColumn.grid(row=0, column=0, sticky="nsew", padx=(5, 2))

    Divider = tk.Frame(MainRow, bg="#555", width=4)
    Divider.grid(row=0, column=1, sticky="ns")

    RightColumn = tk.Frame(MainRow)
    RightColumn.grid(row=0, column=2, sticky="nsew", padx=(2, 5))
    BuildUI()





def ClearOutput(key):
    Devices["A"][key] = None
    RebuildUI()

def ClearInput(key):
    Devices["M"][key] = None
    RebuildUI()

def OpenOutputPopup(targetKey):
    RefreshOutputDevices()

    Popup = tk.Toplevel(Root)
    Popup.title("Select Output Device")
    Popup.geometry("400x500")
    Popup.grab_set()

    for device in OutputDevices:
        tk.Button(
            Popup,
            text=device["UIName"],
            command=lambda d=device: SelectOutputDevice(d, targetKey, Popup)
        ).pack(fill="x")

def SelectOutputDevice(device, key, Popup):
    Devices["A"][key] = {
        "Name": device["UIName"],
        "ID": device["SystemID"],
        "Volume": 100,
        "Dominant": False
    }

    RebuildUI()
    SaveConfig()
    Popup.destroy()

def OpenInputPopup(targetKey):
    RefreshInputDevices()

    Popup = tk.Toplevel(Root)
    Popup.title("Select Input Device")
    Popup.geometry("400x500")
    Popup.grab_set()

    for device in InputDevices:
        tk.Button(
            Popup,
            text=device["UIName"],
            command=lambda d=device: SelectInputDevice(d, targetKey, Popup)
        ).pack(fill="x")

def SelectInputDevice(device, key, Popup):
    Devices["M"][key] = {
        "Name": device["UIName"],
        "ID": device["SystemID"],
        "Volume": 100,
        "Dominant": False
    }
    SaveConfig()
    RebuildUI()
    Popup.destroy()


#------------------------------------------- Heartbeat
def ApplySources():
    active = GetAudioSources()

    for name, sink in Sinks.items():
        for src in sink["Sources"]:
            if src in active:
                SourceConnection(name, src)

def ApplyOutputs():
    for name, sink in Sinks.items():
        for d, enabled in sink["Outputs"].items():
            if not enabled:
                continue

            device = Devices["A"].get(d)
            if not device:
                print(f"Audio Device not found for {device['Name']}")
                continue

            device_id = ResolveSinkID(device["Name"])
            if not device_id:
                print(f"Audio Device ID not found for {device['Name']}")
                continue

            if device["ID"] != device_id:
                device["ID"] = device_id
                SaveConfig()

            subprocess.run([
                "./NW.sh",
                "ConnectSinkToAux",
                name,
                device_id,
                str(int(sink["Mono"]))
            ])

def ApplyInputs():
    for name, sink in Sinks.items():
        for d, enabled in sink["Inputs"].items():
            if not enabled:
                continue

            device = Devices["M"].get(d)
            if not device:
                continue

            device_id = ResolveSourceID(device["Name"])
            if device["ID"] != device_id:
                device["ID"] = device_id
                SaveConfig()

            subprocess.run([
                "./NW.sh",
                "ConnectMicToSink",
                name,
                device_id,
            ])

def GetSinkVolume(sink):
    try:
        out = subprocess.check_output(
            ["pactl", "get-sink-volume", sink]
        ).decode()

        for part in out.split():
            if "%" in part:
                return int(part.replace("%", ""))
    except:
        pass

    return None

def ApplyDominantVolumes():
    for name, sink in Sinks.items():
        if not sink.get("Dominant"):
            continue

        target = int(sink.get("Volume", 1.0) * 100)
        current = GetSinkVolume(name)

        if current is None:
            continue

        # only correct if drifted (prevents spam)
        if abs(current - target) > 2:
            subprocess.run([
                "pactl", "set-sink-volume",
                name,
                f"{target}%"
            ])

def EnforceSinkVolumes():
    for name, sink in Sinks.items():
        target = sink.get("Volume")
        if target is None:
            continue

        current = GetSinkVolume(name)
        if current is None:
            continue

        if abs(current - target) > 2:
            print(f"Fixing volume for {name}: {current} → {target}")

            subprocess.run([
                "./NW.sh",
                "SetSinkVolume",
                name,
                str(target)
            ])

# ==============================
# Startup
# ==============================
def Startup():
    for name, sink in Sinks.items():
        # create sink
        subprocess.run(["./NW.sh", "CreateSink", name])
        # outputs
        for d, enabled in sink["Outputs"].items():

            device = Devices["A"].get(d)
            if not device or not enabled:
                continue

            subprocess.run([
                "./NW.sh",
                "ConnectSinkToAux",
                name,
                device["ID"],
                str(int(sink["Mono"]))
            ])

        # inputs
        for d, enabled in sink["Inputs"].items():
            device = Devices["M"].get(d)
            if not device or not enabled:
                continue

            subprocess.run([
                "./NW.sh",
                "ConnectMicToSink",
                device["ID"],
                name
            ])

        # sources
        for src in sink["Sources"]:
            subprocess.run([
                "./NW.sh",
                "ConnectSourceToSink",
                src,
                name
            ])



subprocess.run(["./NW.sh", "ClearSinks"])
LoadConfig()
Startup()
RebuildUI()
RefreshRoutingUI()



# ==============================
# Threads / Shutdown
# ==============================
def WatchDevices():
    global LastOutputs, LastInputs, LastSources

    LastOutputs = set()
    LastInputs = set()
    LastSources = set()

    tick = 0

    while True:
        try:
            if tick == 0:
                
                RefreshOutputDevices()
            
                for key, device in Devices["A"].items():
                    if not device:
                        continue
                    vol = GetAudioDeviceVolume(device["ID"])
                    if vol is None:
                        continue
                    if vol != device["Volume"] and device["Dominant"]:
                        subprocess.run([
                        "pactl",
                        "set-sink-volume",
                        device["ID"],
                        f"{device['Volume']}%"
                        ])


                current =  {device["SystemID"] for device in OutputDevices}
                if current != LastOutputs:
                    print("Outputs changed")
                    ApplyOutputs() 
                    LastOutputs = current

            elif tick == 1:
                RefreshInputDevices()

                for key, device in Devices["M"].items():
                    if not device:
                        continue
                    vol = GetMicrophoneVolume(device["ID"])
                    if vol is None:
                        continue
                    if vol != device["Volume"] and device["Dominant"]:
                        subprocess.run([
                        "pactl",
                        "set-source-volume",
                        device["ID"],
                        f"{device['Volume']}%"
                        ])



                current = {d["ID"] for d in InputDevices}

                if current != LastInputs:
                    print("Inputs changed")
                    ApplyInputs()
                    LastInputs = current

            elif tick == 2:
                EnforceSinkVolumes()
                current = set(GetAudioSources())

                if current != LastSources:
                    print("Sources changed")
                    ApplySources()
                    LastSources = current

            tick = (tick + 1) % 3
            time.sleep(1)

        except Exception as e:
            print("WatchDevices error:", e)
            time.sleep(2)

def OnClose():
    Root.withdraw()

Root.protocol("WM_DELETE_WINDOW", OnClose)

threading.Thread(target=WatchDevices, daemon=True).start()
threading.Thread(target=StartTray, daemon=True).start()

Root.mainloop()