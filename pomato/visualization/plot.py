"""This is the bokeh plot, consisting of the worst code ever"""
import json
# pylint: disable-msg=C0103
import os.path
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from bokeh import palettes
from bokeh.io import curdoc, show
from bokeh.layouts import column, row, widgetbox
from bokeh.models import (
    Circle, HoverTool, Label, LassoSelectTool, MultiLine, Select, TapTool,
    WMTSTileSource)
from bokeh.models.widgets import RadioButtonGroup, Slider
from bokeh.plotting import ColumnDataSource, figure
from bokeh.tile_providers import Vendors, get_provider


def get_tilesource(provider="STAMEN_TONER_BACKGROUND"):
  tile_source = get_provider(provider)
  return tile_source

def init_market_data(market_db):
    """load data from market_result/market_db forder"""
    data_dir = WDIR.joinpath("market_result").joinpath(market_db)

    nodes = pd.read_csv(data_dir.joinpath("nodes.csv"), index_col=0)
    g_by_fuel = pd.read_csv(data_dir.joinpath("g_by_fuel.csv"), index_col=0)
    demand = pd.read_csv(data_dir.joinpath("demand.csv"), index_col=0)
    inj = pd.read_csv(data_dir.joinpath("inj.csv"), index_col=0)
    f_dc = pd.read_csv(data_dir.joinpath("f_dc.csv"), index_col=0)
    t_dict = json.load(open(data_dir.joinpath("t.json")))

    lines = pd.read_csv(data_dir.joinpath("lines.csv"), index_col=0)
    dclines = pd.read_csv(data_dir.joinpath("dclines.csv"), index_col=0)
    lodf_matrix = pd.read_csv(data_dir.joinpath("lodf.csv"), index_col=0).round(4)
    n_1_flows = pd.read_csv(data_dir.joinpath("n_1_flows.csv"), index_col=0)
    n_0_flows = pd.read_csv(data_dir.joinpath("n_0_flows.csv"), index_col=0)

    return (nodes, g_by_fuel, demand, inj, f_dc, t_dict["t_first"], t_dict["t_last"],
            lines, dclines, lodf_matrix, n_0_flows, n_1_flows)

def all_fuels_from_marketdbs():
    """ Find all Fuels from Market Result to correctly show legend"""
    marketdbs = [path for path in os.listdir(WDIR.joinpath("market_result")) if "." not in path]
    fuels = ["dem"]
    for database in marketdbs:
        data_dir = WDIR.joinpath("market_result").joinpath(database)
        g_by_fuel = pd.read_csv(data_dir.joinpath("g_by_fuel.csv"), index_col=0)
        add_fuels = [fuel for fuel in list(g_by_fuel.fuel.unique()) if fuel not in fuels]
        fuels.extend(add_fuels)
    return fuels

def update_market_data(attr, old, new):
    """update market data"""
    label.text = "Loading Market Data..."
    source_ind.data["color"] = ["red"]
    (nodes, g_by_fuel, demand, inj, f_dc, t_first, t_last,
     lines, dclines, lodf_matrix, n_0_flows, n_1_flows) = init_market_data(select_market_db.value)
    ## Update Data Sources
    source_nodes_data = ColumnDataSource.from_df(nodes)
    source_g_fuel_data.data = ColumnDataSource.from_df(g_by_fuel)
    source_d_data.data = ColumnDataSource.from_df(demand)
    source_inj_data.data = ColumnDataSource.from_df(inj)
    source_f_dc_data.data = ColumnDataSource.from_df(f_dc)
    source_n_0_flows_data.data = ColumnDataSource.from_df(n_0_flows)
    source_n_1_flows_data.data = ColumnDataSource.from_df(n_1_flows)
    source_lines_data.data = ColumnDataSource.from_df(lines)
    source_dclines_data.data = ColumnDataSource.from_df(dclines)
    source_lodf_data.data = ColumnDataSource.from_df(lodf_matrix)

    ### Update Data Sources for the plots
    nodes_dict = create_nodes_source(nodes)
    source_nodes.data = nodes_dict
    line_dict = create_line_source(lines, nodes)
    source_lines.data = line_dict
    dcline_dict = create_dc_line_source(dclines, nodes)
    source_dclines.data = dcline_dict

    slider.start = t_first
    slider.end = t_last
    slider.value = t_first
    label.text = "Data is Loaded!"
    source_ind.data["color"] = ["green"]

def merc(lat, lon):
    """convert lat lon to x,y"""
    r_major = 6378137.000
    coord_x = r_major * np.radians(lon)
    scale = coord_x/lon
    coord_y = 180.0/np.pi * np.log(np.tan(np.pi/4.0 + lat * (np.pi/180.0)/2.0)) * scale
    return(coord_x, coord_y)

def available_files_by_ext(folder, ext):
    """ check folder for files with ext"""
    list_files = []
    for file in folder.rglob(f"*.{ext}"):
        list_files.append(file.name)
    return list_files

def update_line_colors(lines, n_0_flows, n_1_flows,
                       option=0, range_start=0, range_end=100):
    """Line colors in 10 shades of RedYellowGreeen palette"""
    ## 0: N-0 Flows, 1: N-1 Flows 2: Line voltage levels
    # timesteps = 't'+ "{0:0>4}".format(int(slider.value))
    stepsize = round((range_end - range_start)/10, 3)
    steps = [range_start + i*stepsize for i in range(0, 10)]
    n_0_flows = n_0_flows.to_frame()
    n_0_flows.columns = ["flow"]
    n_1_flows = n_1_flows.to_frame()
    n_1_flows.columns = ["flow"]

    if option == 0:
        n_0_flows["alpha"] = 0.4
        n_0_flows["color"] = palettes.RdYlGn[10][0]
        for idx, loading in enumerate(steps):
            cond = abs(n_0_flows.flow.values)/lines.maxflow > loading/100
            n_0_flows.loc[cond, "color"] = palettes.RdYlGn[10][idx]
        color = list(n_0_flows.color.values)
        line_alpha = list(n_0_flows.alpha.values)

    elif option == 1:
        n_1_flows["alpha"] = 0.4
        n_1_flows["color"] = palettes.RdYlGn[10][0]
        for idx, loading in enumerate(steps):
            cond = abs(n_1_flows.flow.values)/lines.maxflow > loading/100
            n_1_flows.loc[cond, "color"] = palettes.RdYlGn[10][idx]
        color = list(n_1_flows.color.values)
        line_alpha = list(n_1_flows.alpha.values)

    elif option == 2:
        color = []
        line_alpha = []
        type_color = {380: 'red', 220: 'green', 150: 'black'}
        if "cnec" in lines.columns:
            for line in lines.index:
                if lines.cnec[line]:
                    color.append("blue")
                    line_alpha.append(1.0)
                elif lines.cb[line]:
                    color.append("purple")
                    line_alpha.append(1.0)
                else:
                    color.append(type_color[lines.type[line]])
                    line_alpha.append(0.1)
        else:
            for line in lines.index:
                color.append(type_color[lines.type[line]])
                line_alpha.append(0.6)

    return color, line_alpha

def create_line_legend(range_start, range_end):
    """
    range = (from, to)
    steps = 10

    returns source
    """
    stepsize = round((range_end - range_start)/10, 3)
    steps = [range_start + i*stepsize for i in range(0, 10)]
    line_legend_dict = {}
    line_legend_dict["top"] = [1 for i in steps]
    line_legend_dict["bottom"] = [0 for i in steps]
    line_legend_dict["left"] = [i for i in steps]
    line_legend_dict["right"] = [i + stepsize for i in steps]
    line_legend_dict["color"] = [palettes.RdYlGn[10][i] for i in range(0, 10)]
    return line_legend_dict

def injections(timestep_int):
    """update net injection depending of t"""
    df_inj = source_inj_data.to_df()
    timestep = 't'+ "{0:0>4}".format(int(timestep_int))
    return list(df_inj[(df_inj.t == timestep)].INJ.values)

def dclines_flow(timestep_int):
    """return flows on dclines at timestep t"""
    timestep = 't'+ "{0:0>4}".format(int(timestep_int))
    df_dclines = source_dclines_data.to_df()
    df_dc_flow = source_f_dc_data.to_df()
    df_dc_flow["dc"] = pd.Categorical(df_dc_flow["dc"],
                                      df_dclines["index"])

    return list(df_dc_flow[df_dc_flow.t == timestep].sort_values("dc").F_DC)

def n_0_flow(timestep_int):
    """return N-0 flows on lines at timestep t"""
    timestep = 't'+ "{0:0>4}".format(int(timestep_int))
    n_0_flows = source_n_0_flows_data.to_df()
    return list(n_0_flows[timestep])

def n_1_flow(timestep_int):
    """return N-1 flows on lines at timestep t"""
    timestep = 't'+ "{0:0>4}".format(int(timestep_int))
    n_1_flows = source_n_1_flows_data.to_df()
    return list(n_1_flows[timestep])

### Bokeh Core Function which are associated with WIdgets
def update_node_injections(attrname, old, new):
    """Updates net injections"""
    source_nodes.data["inj"] = injections(slider.value)

def update_line_loadings(attrname, old, new):
    """Updates Lineloadings"""

    legend_options = {0: {"from": 60, "to": 105, "title": "N-0 Lineloadings in %"},
                      1: {"from": 60, "to": 105, "title": "N-1 Lineloadings in %"},
                      2: {"from": 60, "to": 105, "title": "Showing Line Info"}}

    source_line_legend.data = create_line_legend(legend_options[flow_type_botton.active]["from"],
                                                 legend_options[flow_type_botton.active]["to"])

    legend_lines.title.text = legend_options[flow_type_botton.active]["title"]
    legend_lines.x_range.start = legend_options[flow_type_botton.active]["from"]
    legend_lines.x_range.end = legend_options[flow_type_botton.active]["to"]*1.005



    source_lines.data["color"], source_lines.data["line_alpha"] = \
        update_line_colors(source_lines_data.to_df(),
                           n_0_flow(slider.value),
                           n_1_flow(slider.value),
                           option=flow_type_botton.active,
                           range_start=legend_options[flow_type_botton.active]["from"],
                           range_end=legend_options[flow_type_botton.active]["to"])

    source_lines.data["flow"] = n_0_flow(slider.value)
    source_lines.data["n_1_flow"] = n_1_flow(slider.value)
    source_dclines.data["flow"] = dclines_flow(slider.value)

def update_stacked_bars(attrname, old, new):
    """Updates Stacked Bar Plot"""
    nodes = []
    for i in n.data_source.selected.indices:
        nodes.append(source_nodes.data["node"][i])
    if nodes != []:
#        print(nodes)
        gen_dict, y_max, legend_dict = create_stacked_bars_sources(nodes)
        source_stacked_bars.data = gen_dict
        source_legend.data = legend_dict
        fig_bar.y_range.end = np.ceil(y_max/2000)*2000
    else:
        print("No Nodes selected")

def create_stacked_bars_sources(nodes):
    """ Creates Data Source Object for Stacked Barplot"""
    gen_dict, y_max = gen_fuel(int(slider.value), nodes)
    list_fuels = list(gen_dict.keys())
    list_fuels.remove("type")

#    gen_dict["stackers"] = list_fuels
#    gen_dict["c"] = palettes.viridis(len(list_fuels))
    x_axis, y_axis, legend, color = [], [], [], []
    for idx, fuel in enumerate(list_fuels):
        if sum(gen_dict[fuel]) != 0:
            legend.append(fuel)
            color.append(palettes.viridis(len(list_fuels))[idx])
            x_axis.append("gen")
            y_axis.append(-1)

    legend_dict = {"x": x_axis, "y": y_axis, "legend": legend, "c":color}
    return gen_dict, y_max, legend_dict

def update_lodf_color(attrname, old, new):
    """Updates LODF colors of lines"""
    color = ["#bababa"] + palettes.RdYlGn[11]
    lodf = source_lodf_data.to_df().set_index("index")
    if l.data_source.selected.indices:
        idx = l.data_source.selected.indices[0]
        sel_line = source_lines.data["line"][idx]
        max_perc = 10e-2
        min_perc = 1e-2
        tmp = lodf.loc[sel_line].abs() * lines.maxflow / lines.loc[sel_line].maxflow
        tmp[tmp < min_perc] = min_perc
        tmp[tmp > max_perc] = max_perc
        colors = [color[int((x - min_perc)*11/(max_perc - min_perc))] for x in  tmp]
        colors[idx] = "blue"

        line_alpha = [0.3 if c == "#bababa" else 0.8 for c in colors]

        source_line_legend.data = create_line_legend(min_perc, max_perc)
        legend_lines.title.text = "Sensitivity towards selected line in %"
        legend_lines.x_range.start, legend_lines.x_range.end = min_perc, max_perc*1.005
    else:
        colors, line_alpha = update_line_colors(source_lines_data.to_df(), n_0_flow(slider.value),
                                                n_1_flow(slider.value), option=flow_type_botton.active)

    source_lines.data["color"] = colors
    source_lines.data["line_alpha"] = line_alpha

## Create/Init source objects
def gen_fuel(t, nodes=None):
    """Generate source for Generation/Demand in Bar-Plot"""
    ## Plot consists of all gen fuels and demand
    ## - first column only gen - second column only demand
    if not nodes:
        nodes = [source_nodes_data.to_df().loc[0, "index"]]
    gen_fuel = source_g_fuel_data.to_df()
    demand = source_d_data.to_df()
    demand = demand.drop("index", axis=1)
    gen_fuel = gen_fuel.drop("index", axis=1)

    t = 't'+ "{0:0>4}".format(int(t))
    tmp = gen_fuel[(gen_fuel.t == t)&(gen_fuel.node.isin(nodes))].groupby("fuel").sum()
    gen_max = tmp.values.sum()
    tmp["D"] = 0
    fuel_dict = {}
    possible_fuels = all_fuels_from_marketdbs()
    for i in possible_fuels:
        if i in tmp.index:
            custom_list = tmp.loc[i].tolist()
            fuel_dict[i] = custom_list
        else:
            fuel_dict[i] = [0, 0]
    fuel_dict["type"] = ["gen", "dem"]

    dem_max = demand.d_total[(demand.n.isin(nodes))&(demand.t == t)].sum()

    fuel_dict["dem"] = [0, dem_max]
    return fuel_dict, max(dem_max, gen_max)

def prepare_line_plot(lines, nodes):
    # Add Columns to lines with total systems and an index
    # so each line from a system has an relative index e.g. 1/3 or 4/5
    tmp = lines[["node_i", "node_j"]].copy()
    tmp.loc[:, "systems"] = 1
    tmp = tmp.groupby(["node_i", "node_j"]).sum()
    tmp = tmp.reset_index()
    lines.loc[:, "systems"] = 1
    lines.loc[:, "no"] = 1
    for node_i, node_j, systems in zip(tmp.node_i, tmp.node_j, tmp.systems):
        condition = (lines.node_i == node_i)&(lines.node_j == node_j)
        lines.loc[condition, "systems"] = systems
        # np.array bc of bug when assining a 2-elm list
        lines.loc[condition, "no"] = np.array([nr for nr in range(0, systems)])

    lx, ly = [], []
    for l in lines.index:
        if lines.systems[l] == 1:
            xi, yi = merc(nodes.lat[lines.node_i[l]], nodes.lon[lines.node_i[l]])
            xj, yj = merc(nodes.lat[lines.node_j[l]], nodes.lon[lines.node_j[l]])
            lx.append([xi, (xi + xj)*0.5, xj])
            ly.append([yi, (yi + yj)*0.5, yj])
        else:
            xi, yi = merc(nodes.lat[lines.node_i[l]], nodes.lon[lines.node_i[l]])
            xj, yj = merc(nodes.lat[lines.node_j[l]], nodes.lon[lines.node_j[l]])
            mx = xj - xi
            my = yj - yi
            # multiple lines are spread across a circle with radius d around each node
            # starting from PI/4 in equal steps ( in angle) to -PI/4 from referece poin
            # reference point is the intersection of the circle and the line to the other node
            # the 20 and pi/5 are purely visual
            d = 36*np.power((np.sqrt(np.power(mx, 2) + np.power(my, 2))), 1/3)
            idx = lines.no[l]/(lines.systems[l] - 1) - 0.5
            if mx == 0:
                alpha = np.pi/4*idx + np.pi/2
                alpha2 = 3/2*np.pi - np.pi/4*idx
            elif mx > 0: # bottom left -> top right | top left -> bottom right
                alpha = np.arctan(my/mx) + np.pi/4*idx
                alpha2 = np.arctan(my/mx) + np.pi - np.pi/4*idx
            elif mx < 0: # bottom right -> top left | top right -> bottom right
                alpha2 = np.arctan(my/mx) + np.pi/4*idx
                alpha = np.arctan(my/mx) + np.pi - np.pi/4*idx

            # lx contains start point, point on circle for mult lines on start point,
            # a point 1/2 of the way for the hover menue to stick to
            # point on circle for mult lines on end point, end point
            lx.append([xi, xi + np.cos(alpha)*d,
                       0.5*(xi + np.cos(alpha)*d + xj + np.cos(alpha2)*d),
                       xj + np.cos(alpha2)*d, xj])
            ly.append([yi, yi + np.sin(alpha)*d,
                       0.5*(yi + np.sin(alpha)*d + yj + np.sin(alpha2)*d),
                       yj + np.sin(alpha2)*d, yj])
    return lx, ly

def create_line_source(lines, nodes):
    """Creates Line Data Source Object"""
    lx, ly = prepare_line_plot(lines, nodes)
    color, line_alpha = update_line_colors(source_lines_data.to_df(),
                                           n_0_flow(slider.value),
                                           n_1_flow(slider.value))
    line_dict = {"lx": lx, "ly": ly,
                 "line": list(lines.index),
                 "max_flow": list(lines.maxflow),
                 "flow": n_0_flow(slider.value),
                 "n_1_flow": n_1_flow(slider.value),
                 "node_i": list(lines.node_i),
                 "node_j": list(lines.node_j),
                 "contingency": list(lines.contingency),
                 "color": color,
                 "line_alpha": line_alpha}

    return line_dict

def create_dc_line_source(dclines, nodes):
    """DC Line Source Object"""
    lx_dc, ly_dc = [], []
    for l in dclines.index:
        xi, yi = merc(nodes.lat[dclines.node_i[l]], nodes.lon[dclines.node_i[l]])
        xj, yj = merc(nodes.lat[dclines.node_j[l]], nodes.lon[dclines.node_j[l]])
        lx_dc.append([xi, (xi+xj)/2, xj])
        ly_dc.append([yi, (yi+yj)/2, yj])

    dcline_dict = {"lx": lx_dc,
                   "ly": ly_dc,
                   "line": list(dclines.index),
                   "flow": dclines_flow(slider.value),
                   "max_flow": list(dclines.maxflow),
                   "node_i": list(dclines.node_i),
                   "node_j": list(dclines.node_j)}
    return dcline_dict

def create_nodes_source(nodes):
    """Nodes Source Object"""
    coords_x, coords_y, lat, lon = [], [], [], []
    for i in nodes.index:
        coord_x, coord_y = merc(nodes.lat[i], nodes.lon[i])
        coords_x.append(coord_x)
        coords_y.append(coord_y)
        lat.append(nodes.lat[i])
        lon.append(nodes.lon[i])

    nodes_dict = {"x": coords_x,
                  "y": coords_y,
                  "lat": lat,
                  "lon": lon,
                  "node": list(nodes.index),
                  "name": list(nodes.name),
                  "zone": list(nodes.zone),
                  "inj": injections(slider.value)}
    return nodes_dict

def create_static_plot(lines, nodes, dclines, inj, flow_n_0, flow_n_1, flow_dc,
                       redispatch=None, option=0, title=None):

    coords_x, coords_y, lat, lon = [], [], [], []
    for i in nodes.index:
        coord_x, coord_y = merc(nodes.lat[i], nodes.lon[i])
        coords_x.append(coord_x)
        coords_y.append(coord_y)
        lat.append(nodes.lat[i])
        lon.append(nodes.lon[i])

    color, size = [], []
    if isinstance(redispatch, pd.DataFrame):
        redispatch = pd.merge(nodes, redispatch[["node", "delta"]].groupby("node").sum(),
                              how="left", left_index=True, right_index=True).fillna(0)
        max_add_size = 50
        max_redispatch = max(redispatch.delta.abs())
        for i in nodes.index:
            if redispatch.delta[i] == 0:
                color.append(palettes.Category20b[4][3])
                size.append(5)
            else:
                color.append("#009473" if redispatch.delta[i] > 0 else "#BF1932")
                size.append(5 + max_add_size*abs(redispatch.delta[i])/max_redispatch)
    else:
        color = [palettes.Category20b[4][3] for n in nodes.index]
        size = [5 for n in nodes.index]

    nodes_dict = {"x": coords_x,
                  "y": coords_y,
                  "lat": lat,
                  "lon": lon,
                  "node": list(nodes.index),
                  "name": list(nodes.name),
                  "zone": list(nodes.zone),
                  "inj": list(inj),
                  "color": color,
                  "size": size}

    lx, ly = prepare_line_plot(lines, nodes)


    color, line_alpha = update_line_colors(lines, flow_n_0, flow_n_1, option=option)

    line_dict = {"lx": lx, "ly": ly,
             "line": list(lines.index),
             "max_flow": list(lines.maxflow),
             "flow": list(flow_n_0.values),
             "n_1_flow": list(flow_n_1.values),
             "node_i": list(lines.node_i),
             "node_j": list(lines.node_j),
             "contingency": list(lines.contingency),
             "color": color,
             "line_alpha": line_alpha}

    # if flow_dc.empty:
    #     flow_dc = np.array([])

    lx_dc, ly_dc = [], []
    for l in dclines.index:
        xi, yi = merc(nodes.lat[dclines.node_i[l]], nodes.lon[dclines.node_i[l]])
        xj, yj = merc(nodes.lat[dclines.node_j[l]], nodes.lon[dclines.node_j[l]])
        lx_dc.append([xi, (xi+xj)/2, xj])
        ly_dc.append([yi, (yi+yj)/2, yj])



    dcline_dict = {"lx": lx_dc,
                   "ly": ly_dc,
                   "line": list(dclines.index),
                   "flow": list(flow_dc.values),
                   "max_flow": list(dclines.maxflow),
                   "node_i": list(dclines.node_i),
                   "node_j": list(dclines.node_j)}

    # Main plot
    ## Dimensions of map (=de)
    lat_max, lat_min = nodes.lat.max(), nodes.lat.min()
    lon_max, lon_min = nodes.lon.max() + 0.2, nodes.lon.min() - 0.2
    x_range, y_range = [], []
    for coord in [[lat_min, lon_min], [lat_max, lon_max]]:
        x, y = merc(coord[0], coord[1])
        x_range.append(x)
        y_range.append(y)

    hover_line = [("Line", "@line"),
                  ("Node_i", "@node_i"),
                  ("Node_j", "@node_j"),
                  ("Capacity", "@max_flow"),
                  ("Flow", "@flow"),
                  ("N-1 Flow", "@n_1_flow"),
                  ("Contingency", "@contingency")]

    hover_dcline = [("Line", "@line"),
                    ("Node_i", "@node_i"),
                    ("Node_j", "@node_j"),
                    ("Capacity", "@max_flow"),
                    ("Flow", "@flow")]

    hover_node = [("Node", "@node"),
                  ("Name", "@name"),
                  ("Zone", "@zone"),
                  ("(lat,lon)", "(@lat, @lon)"),
                  ("Inj", "@inj")]

    fig = figure(tools="pan,wheel_zoom", active_scroll="wheel_zoom", title=title,
                 x_range=(x_range), y_range=(y_range), plot_height=700, plot_width=800)

    STAMEN_LITE = get_tilesource()
    fig.add_tile(STAMEN_LITE)
    fig.axis.visible = False

    # lines and dc lines as line plots
    l = fig.multi_line("lx", "ly", color="color", hover_line_color='color',
                       line_width=3, line_alpha="line_alpha",
                       hover_line_alpha=1.0, source=line_dict)

    dc = fig.multi_line("lx", "ly", color="blue", hover_line_color='blue',
                        line_width=3, line_alpha=0.6, hover_line_alpha=1.0,
                        line_dash="dashed", source=dcline_dict)

    # hover tool which picks up information from lines and dc lines
    fig.add_tools(HoverTool(renderers=[l], show_arrow=False,
                            line_policy='next', tooltips=hover_line))

    fig.add_tools(HoverTool(renderers=[dc], show_arrow=False,
                            line_policy='next', tooltips=hover_dcline))

    ## nodes plot
    n = fig.circle("x", "y", size="size", fill_alpha=0.8,
                    fill_color="color", source=nodes_dict)

    fig.add_tools(HoverTool(renderers=[n], tooltips=hover_node))

    return fig

if __name__ == "__main__":
    WDIR = Path(sys.argv[1])
    # Init Data
    option_market_db = [path for path in os.listdir(WDIR.joinpath("market_result")) if "." not in path]
    (nodes, g_by_fuel, demand, inj, f_dc, t_first, t_last,
     lines, dclines, lodf_matrix, n_0_flows, n_1_flows) = init_market_data(option_market_db[0])

    ## Define Widgets and function calls
    select_market_db = Select(title="Model Run:", value=option_market_db[0], options=option_market_db)
    slider = Slider(start=t_first, end=t_last, value=t_first, step=1, title="Timestep",
                    callback_throttle=0, callback_policy="throttle") # Throttle doesnt work as of now

    flow_type_botton = RadioButtonGroup(name="Choose Flow Case:", width=300,
                                        labels=["N-0", "N-1", "Voltage Level"], active=0)
    flow_type_botton.on_change('active', update_line_loadings)

    ##Update things when slider or selects are changed
    slider.on_change('value', update_line_loadings)
    slider.on_change('value', update_stacked_bars)
    slider.on_change('value', update_node_injections)

    select_market_db.on_change('value', update_market_data)
    select_market_db.on_change('value', update_stacked_bars)
    select_market_db.on_change('value', update_line_loadings)
    select_market_db.on_change('value', update_node_injections)

    #Store Market Data in ColumnDataSource Object, so it can be changed and retrieved while running
    source_nodes_data = ColumnDataSource(nodes)
    source_g_fuel_data = ColumnDataSource(g_by_fuel)
    source_d_data = ColumnDataSource(demand)
    source_inj_data = ColumnDataSource(inj)
    source_f_dc_data = ColumnDataSource(f_dc)
    source_lines_data = ColumnDataSource(lines)
    source_dclines_data = ColumnDataSource(dclines)
    source_n_0_flows_data = ColumnDataSource(n_0_flows)
    source_n_1_flows_data = ColumnDataSource(n_1_flows)
    source_lodf_data = ColumnDataSource(lodf_matrix)

    ## Init ColumnDataSource for the plot itself
    # This the dict is created in a function so i can be called when running
    nodes_dict = create_nodes_source(nodes)
    source_nodes = ColumnDataSource(nodes_dict)

    line_dict = create_line_source(lines, nodes)
    source_lines = ColumnDataSource(line_dict)

    dcline_dict = create_dc_line_source(dclines, nodes)
    source_dclines = ColumnDataSource(dcline_dict)

    gen_dict, y_max, legend_dict = create_stacked_bars_sources(list(nodes.index))
    source_stacked_bars = ColumnDataSource(gen_dict)
    source_legend = ColumnDataSource(legend_dict)

    hover_line = [("Line", "@line"),
                  ("Node_i", "@node_i"),
                  ("Node_j", "@node_j"),
                  ("Capacity", "@max_flow"),
                  ("Flow", "@flow"),
                  ("N-1 Flow", "@n_1_flow"),
                  ("Contingency", "@contingency")]

    hover_dcline = [("Line", "@line"),
                    ("Node_i", "@node_i"),
                    ("Node_j", "@node_j"),
                    ("Capacity", "@max_flow"),
                    ("Flow", "@flow")]

    hover_node = [("Node", "@node"),
                  ("Name", "@name"),
                  ("Zone", "@zone"),
                  ("(lat,lon)", "(@lat, @lon)"),
                  ("Inj", "@inj")]

    ## bar Chart with generation by fuel
    fig_bar = figure(x_range=["gen", "dem"], y_range=(0, 2000), title="Nodal Generation",
                     toolbar_location=None, tools="", plot_height=750, plot_width=300)

    list_fuels = list(gen_dict.keys())
    list_fuels.remove("type")
    fig_bar.vbar_stack(stackers=list_fuels,
                       x='type', width=.9,
                       color=palettes.viridis(len(list_fuels)),
                       source=source_stacked_bars)

    ## Dummy plot to create the legend for the barplot # Needed bc vbar_stack does
    ## not support to subset the data presented in the legen ( e.g. will always display all fuels)
    fig_bar.circle("x", "y", alpha=1, color="c", legend="legend", source=source_legend)
    fig_bar.y_range.end = np.ceil(y_max/2000)*2000

    # Main plot
    ## Dimensions of map (=de)
    de = [[57, 4.4], [43, 16.4]]
    x_range, y_range = [], []
    for c in de:
        x, y = merc(c[0], c[1])
        x_range.append(x)
        y_range.append(y)

    fig = figure(tools="pan,wheel_zoom,lasso_select,tap", active_scroll="wheel_zoom",
                 x_range=(x_range), y_range=(y_range), plot_width=1500, plot_height=1000)
    fig.axis.visible = False

    # lines and dc lines as line plots
    l = fig.multi_line("lx", "ly", color="color", hover_line_color='color',
                       line_width=3, line_alpha="line_alpha",
                       hover_line_alpha=1.0, source=source_lines)

    dc = fig.multi_line("lx", "ly", color="blue", hover_line_color='blue',
                        line_width=3, line_alpha=0.6, hover_line_alpha=1.0,
                        line_dash="dashed", source=source_dclines)
    # hover tool which picks up information from lines and dc lines
    fig.add_tools(HoverTool(renderers=[l], show_arrow=False,
                            line_policy='next', tooltips=hover_line))

    fig.add_tools(HoverTool(renderers=[dc], show_arrow=False,
                            line_policy='next', tooltips=hover_dcline))

    selected_line = MultiLine(line_color="color", line_alpha="line_alpha", line_width=4)
    l.selection_glyph = selected_line
    l.nonselection_glyph = selected_line
    l.data_source.selected.on_change('multiline_indices', update_lodf_color)

    ## nodes plot
    color = palettes.Category20b[4]
    # color sample for various states normal-hover-selected-notselected
    n = fig.circle("x", "y", size=4, fill_alpha=0.8, fill_color=color[3], source=source_nodes)
    fig.add_tools(HoverTool(renderers=[n], tooltips=hover_node))
    # define color when (not-) selected
    selected_node = Circle(fill_alpha=0.8, fill_color=color[0], line_color=None)
    nonselected_node = Circle(fill_alpha=0.6, fill_color=color[3], line_color=None)
    # and trigger it correctly
    n.selection_glyph = selected_node
    n.nonselection_glyph = nonselected_node

    #dir(n.data_source.selected)
    #n.data_source.on_change('selected', update_stacked_bars)
    n.data_source.selected.on_change('indices', update_stacked_bars)

    #inidcator for data-load
    source_ind = ColumnDataSource(data=dict(x=[1], y=[1], color=["green"]))
    fig_indicator = figure(x_range=(0, 8), y_range=(0, 2), toolbar_location=None,
                           tools="", plot_height=50, plot_width=300)
    label = Label(x=1.8, y=.8, text="Data is Loaded!", text_alpha=1)
    fig_indicator.add_layout(label)
    fig_indicator.axis.visible = False
    fig_indicator.grid.visible = False
    fig_indicator.outline_line_alpha = 0
    fig_indicator.circle("x", "y", size=25, fill_alpha=0.6, fill_color="color",
                         line_color=None, source=source_ind)

    ### Legend for Lineloadings/LODF colors
    line_legend_dict = create_line_legend(60, 110)
    source_line_legend = ColumnDataSource(line_legend_dict)
    legend_lines = figure(plot_width=300, plot_height=80,
                          x_range=(60, 110.1), y_range=(0, 1),
                          toolbar_location=None, tools="",
                          title="N-0 Lineloadings in %"
                          )


    legend_lines.quad(top="top", bottom="bottom", left="left", right="right",
                      color="color", source=source_line_legend)
    legend_lines.yaxis.visible = False
    legend_lines.grid.visible = False
    legend_lines.outline_line_alpha = 0

    # add the geographical map
    fig.add_tile(get_tilesource())
    fig.select(LassoSelectTool).renderers = [n]
    fig.select(LassoSelectTool).select_every_mousemove = False
    fig.select(TapTool).renderers = [l]

    # set up layout = row(row|column)
    # UI sclaing for everthing except the widget column with the inducator plot
    widgets = column(widgetbox(slider, flow_type_botton, select_market_db, width=300),
                     legend_lines, fig_indicator, fig_bar)
    #main_map = row(children=[fig,fig_bar])
    layout = row(children=[fig, widgets], sizing_mode="scale_height")

    curdoc().add_root(layout)
