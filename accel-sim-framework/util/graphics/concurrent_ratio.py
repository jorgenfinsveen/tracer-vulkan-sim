import gzip
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import os

FULL_PATH_ROOT = os.path.expandvars(f"$ACCEL_SIM/sim_run_11.7")

GPU_CONFIGS = {
    "orin": "ORIN-SASS-concurrent-fg-VISUAL",
    "rtx":  "RTX3070-SASS-concurrent-fg-VISUAL"
}

SIM_DATE = "Tue-Dec--2-14-12-31-2025"

render_passes_2k = [
    f"render_passes_2k/all1/{GPU_CONFIGS['orin']}",
    f"render_passes_2k/all1/{GPU_CONFIGS['rtx']}",
    f"render_passes_2k/NO_ARGS/{GPU_CONFIGS['orin']}",
    f"render_passes_2k/NO_ARGS/{GPU_CONFIGS['rtx']}"
]

render_passes_2k_lod0 = [
    f"render_passes_2k_lod0/NO_ARGS/{GPU_CONFIGS['orin']}",
    f"render_passes_2k_lod0/NO_ARGS/{GPU_CONFIGS['rtx']}"
]



filename = "{0}/{1}".format(
    f"{FULL_PATH_ROOT}/{render_passes_2k[0]}",
    f"gpgpusim_visualizer__{SIM_DATE}.log.gz"
)


array = pd.DataFrame(
    columns=["globalcyclecount",'cycle_counter', "tex_line", "verte_lines", "compute", "invalid", "g_count", "c_count", 'dynamic_sm_count']
)

if (filename.endswith('.gz')):
        file = gzip.open(filename, 'rt')
else:
    file = open(filename, 'r')

cycle = 0

for line in file:
    if not line:
        break

    nameNdata = line.split(":")
    if len(nameNdata) != 2:
        # evt. continue i stedet for print
        # print(f"Syntax error at '{line}'")
        continue

    namePart = nameNdata[0].strip()
    dataPart = nameNdata[1].strip()

    if namePart == "globalcyclecount":
        cycle = int(dataPart)
        idx = len(array)
        array.loc[idx, "globalcyclecount"] = cycle
        array.loc[idx, "cycle_counter"] = 500 * idx

    elif namePart == "L2Breakdown":
        if len(array) == 0:
            continue
        data = dataPart.split()
        idx = array.index[-1]
        array.loc[idx, "tex_line"] = int(data[0])
        array.loc[idx, "verte_lines"] = int(data[1])
        array.loc[idx, "compute"] = int(data[2])
        array.loc[idx, "invalid"] = int(data[3])

    elif namePart == "AvgGRThreads":
        if len(array) == 0:
            continue
        idx = array.index[-1]
        array.loc[idx, "g_count"] = float(dataPart)

    elif namePart == "AvgCPThreads":
        if len(array) == 0:
            continue
        idx = array.index[-1]
        array.loc[idx, "c_count"] = float(dataPart)

    elif namePart == "dynamic_sm_count":
        if len(array) == 0:
            continue
        idx = array.index[-1]
        array.loc[idx, "dynamic_sm_count"] = float(dataPart)


import plotly.express as px

fig = px.scatter(x=[0, 1, 2, 3, 4], y=[0, 1, 4, 9, 16])
fig.show()
fig.write_image("./{0}.pdf".format("concurrent"), format="pdf")

fig = go.Figure()

fig.add_trace(go.Scatter(x=array['cycle_counter'], y=array['g_count'] / (1024+512), mode='lines', 
                         hoverinfo='x+y', stackgroup='one', name='Rendering Shader'))
fig.add_trace(go.Scatter(x=array['cycle_counter'], y=array['c_count'] / (1024+512), mode='lines', 
                         hoverinfo='x+y', stackgroup='one', name='Compute Kernel'))


fig.update_layout(
    xaxis_title='Global Cycle',
    yaxis_title='Occupancy',
    xaxis=dict(
        titlefont=dict(size=25, color="black", family="sans-serif"),
        tickfont=dict(size=15, color="black", family="sans-serif"),
        autorange=True,
    ),
    yaxis=dict(
        titlefont=dict(size=25, color="black", family="sans-serif"),
        tickfont=dict(size=15, color="black", family="sans-serif"),
        autorange=True,
    ),
    width=800,
    height=300,
    title_font_family="sans-serif",
    title_font_size=25,
    margin=dict(l=20, r=10, t=50, b=0),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1,
        xanchor="left",
        x=0,
        font=dict(size=20, family="sans-serif")
        
    ),
    title=dict(
        font=dict(size=25, family="sans-serif"),
        text="PT + VIO",
        # text="Occupancy: {0}".format('73.13%'),
        x=0.98,
        y=0.95
    ),

)

fig.write_image("./{0}.pdf".format("concurrent"), format="pdf")
np.average(array['tex_line']/1024/32)
