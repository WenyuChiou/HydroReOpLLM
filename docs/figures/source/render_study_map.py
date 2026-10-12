"""Plot the frozen, unsimplified EPSG:5070 GIS extract without map downloads."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch, Rectangle
import matplotlib.patheffects as effects


def rings(geometry):
    if geometry['type']=='Polygon':return [geometry['coordinates']]
    if geometry['type']=='MultiPolygon':return geometry['coordinates']
    raise ValueError('expected polygon geometry')


def polygon(ax,geometry,**style):
    for part in rings(geometry):
        vertices,codes=[],[]
        for ring in part:
            vertices.extend(ring)
            codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(ring)-2)+[PlotPath.CLOSEPOLY])
        ax.add_patch(PathPatch(PlotPath(vertices,codes),**style))


def render(source,output):
    data=json.loads(source.read_text(encoding='utf-8'))
    assert data['crs']['authority']=='EPSG:5070' and len(data['subbasins'])==7
    plt.rcParams.update({'svg.fonttype':'none','font.family':'DejaVu Sans'})
    fig=plt.figure(figsize=(11,7)); ax=fig.add_axes([.035,.13,.7,.78]); inset=fig.add_axes([.77,.52,.2,.37])
    palette=['#E4D4B0','#C5B18A','#BDD3D9','#D1DCE4','#9FB9C9','#C0CFB4','#A2B898']
    for feature,color in zip(data['subbasins'],palette):
        polygon(ax,feature['geometry'],facecolor=color,edgecolor='#54616A',lw=.7)
        # Place labels at the mean of the largest outer ring; manual edits are
        # confined to text positions and never change source geometry.
        outer=max(rings(feature['geometry']),key=lambda item:len(item[0]))[0]
        x=sum(p[0] for p in outer)/len(outer);y=sum(p[1] for p in outer)/len(outer)
        ax.text(x,y,feature['properties']['subbasin_id'],fontsize=8,ha='center',color='#263238',
                path_effects=[effects.withStroke(linewidth=2,foreground='white')])
    for feature in data['layers']['river_network']:
        geometry=feature['geometry']
        lines=[geometry['coordinates']] if geometry['type']=='LineString' else geometry['coordinates']
        for line in lines:
            ax.plot(*zip(*line),color='#487B93',lw=.65,alpha=.8)
    for feature in data['layers']['reservoirs']:
        polygon(ax,feature['geometry'],facecolor='#4C91AA',edgecolor='#32647B',lw=.7)
    for feature in data['layers']['usgs_gauges']:
        x,y=feature['geometry']['coordinates'];label='USGS '+feature['properties']['usgs_id']
        ax.scatter([x],[y],marker='^',color='#1C1C1C',s=45,zorder=8)
        ax.annotate(label,(x,y),xytext=(x-7500,y+2800),fontsize=9,
                    arrowprops={'arrowstyle':'-','color':'#1C1C1C'},
                    bbox={'facecolor':'white','edgecolor':'none','alpha':.85,'pad':2})
    for feature in data['layers']['map_points']:
        x,y=feature['geometry']['coordinates'];dam='OUTLET' in feature['properties']['point_id']
        ax.scatter([x],[y],marker='s' if dam else 'o',color='#945647' if dam else '#1D6A83',s=42,zorder=9)
        ax.annotate('Dam / outlet*' if dam else 'River inlet*',(x,y),xytext=(x-3500,y-4200 if dam else y+1900),fontsize=9,
                    arrowprops={'arrowstyle':'-','color':'#444444'},bbox={'facecolor':'white','edgecolor':'none','alpha':.85,'pad':2})
    xmin,ymin,xmax,ymax=data['viewport_bounds_epsg5070'];pad=1800
    ax.set(xlim=(xmin-pad,xmax+pad),ylim=(ymin-pad,ymax+pad));ax.set_aspect('equal');ax.axis('off')
    ax.plot([xmin+1000,xmin+11000],[ymin+800,ymin+800],color='black',lw=2);ax.text(xmin+6000,ymin+1700,'10 km',ha='center',fontsize=9)
    ax.annotate('N',xy=(xmax-1300,ymax-1000),xytext=(xmax-1300,ymax-5200),ha='center',fontsize=11,
                arrowprops={'arrowstyle':'-|>','color':'#263238','lw':1.5})
    basin=data['layers']['delaware_river_basin'][0]['geometry']
    polygon(inset,basin,facecolor='#ECEFEA',edgecolor='#778174',lw=.7)
    outer=rings(basin)[0][0];xs,ys=zip(*outer)
    inset.set(xlim=(min(xs)-10000,max(xs)+10000),ylim=(min(ys)-10000,max(ys)+10000));inset.set_aspect('equal');inset.axis('off')
    inset.add_patch(Rectangle((xmin,ymin),xmax-xmin,ymax-ymin,fill=False,edgecolor='#945647',lw=1.2))
    inset.set_title('Delaware River Basin',fontsize=10)
    fig.text(.78,.46,'Model subbasins',fontsize=11,weight='bold')
    for i,(feature,color) in enumerate(zip(data['subbasins'],palette)):
        y=.42-i*.031;fig.patches.append(Rectangle((.78,y),.015,.018,facecolor=color,transform=fig.transFigure,edgecolor='#666',lw=.4))
        fig.text(.805,y,feature['properties']['subbasin_id'],fontsize=9)
    fig.text(.78,.115,'▲ USGS gauge\nBlue lines: rivers\nEPSG:5070',fontsize=9,linespacing=1.6)
    fig.suptitle('FE Walter: seven model subbasins',fontsize=17,weight='bold',y=.97)
    fig.text(.045,.045,'Sources: frozen NHDPlus HR / NLDI / WBD GIS. *Outlet: project record; inlet: derived boundary crossing.',fontsize=8)
    output.parent.mkdir(parents=True,exist_ok=True)
    for extension in ('svg','pdf','png'):fig.savefig(output.with_suffix('.'+extension),dpi=200,facecolor='white')
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=Path('data/figures/fe_walter_map.json'));parser.add_argument('--output',type=Path,default=Path('docs/figures/fe-walter-study-map'))
    args=parser.parse_args();render(args.source,args.output)
