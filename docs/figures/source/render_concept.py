"""Render editable architecture SVG/PDF and README PNG without external services."""
from pathlib import Path
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


def render(output, language='en'):
    plt.rcParams['svg.fonttype'] = 'none'
    plt.rcParams['font.family'] = 'Microsoft JhengHei' if language == 'zh-TW' else 'DejaVu Sans'
    fig, ax = plt.subplots(figsize=(12, 5.8))
    ax.set(xlim=(0,12),ylim=(0,5.8)); ax.axis('off')
    ink,water,decision,state='#223238','#566C73','#897D55','#707C74'
    labels = (['HydroCNHS + reservoir decisions','Existing HydroCNHS','Added decision system',
               'Weather','Runoff','Upstream routing','Added physics','Downstream routing','River flow',
               'Observation','Rule-based','Zero-shot','DKP','Requested release','Next-day state','Audit / trace',
               'Dam API','Water','Decision','State'] if language=='en' else
              ['HydroCNHS＋水庫決策','原版 HydroCNHS','新增決策系統','氣象','產流','上游 routing','新增物理求解',
               '下游 routing','河川流量','當日狀態','規則基準','Zero-shot','DKP','請求放流','下一日狀態',
               'Audit／trace','Dam API','水流','決策','狀態'])
    def text(x,y,label,size=12,**kw):ax.text(x,y,label,ha='center',va='center',fontsize=size,color=ink,**kw)
    def box(x,y,w,h,label,color):
        ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=0.03,rounding_size=0.1',
                    facecolor=color,edgecolor=ink,lw=.7));text(x,y,label,11 if 'routing' in label else 12)
    def edge(points,color,style='-',width=1.7):
        for a,b in zip(points[:-2],points[1:-1]): ax.plot([a[0],b[0]],[a[1],b[1]],color=color,lw=width,ls=style)
        ax.add_patch(FancyArrowPatch(points[-2],points[-1],arrowstyle='-|>',mutation_scale=14,color=color,lw=width,ls=style))
    text(6,5.55,labels[0],18,weight='bold')
    ax.add_patch(FancyBboxPatch((.2,1.2),11.6,1.7,boxstyle='round,pad=.05',facecolor='#F2F5F5',edgecolor=water,lw=1))
    text(1.5,1.4,labels[1],11)
    ax.add_patch(FancyBboxPatch((3.1,3.4),5.1,1.75,boxstyle='round,pad=.05',facecolor='#FBF8EF',edgecolor=decision,lw=1))
    text(4.4,4.93,labels[2],11)
    for x,w,label in [(1,1.2,labels[3]),(2.6,1.25,labels[4]),(4.45,1.9,labels[5]),
                      (6.65,1.8,labels[6]),(9,2,labels[7]),(11.1,1.25,labels[8])]:
        box(x,2.1,w,.72,label,'#EFE7D4' if x==6.65 else '#E0E9EB')
    for a,b in [(1.62,1.94),(3.24,3.46),(5.42,5.72),(7.57,7.96),(10.04,10.43)]:
        edge([(a,2.1),(b,2.1)],water)
    text(6.65,2.67,labels[16],10)
    box(4.15,3.8,1.7,.62,labels[9],'#E0E9EB')
    # These are mutually exclusive decision backends for the same observation.
    for y,label in [(4.6,labels[10]),(4.1,labels[11]),(3.6,labels[12])]:
        box(6.65,y,1.8,.46,label,'#EFE7D4')
        edge([(5.03,3.8),(5.45,3.8),(5.45,y),(5.72,y)],decision,'--',1.2)
        edge([(7.57,y),(7.88,y),(7.88,2.85),(6.65,2.85),(6.65,2.49)],decision,'--',1.2)
    edge([(4.45,2.49),(4.45,3.47)],state,':')
    edge([(6.2,2.49),(6.2,3.07),(4.15,3.07),(4.15,3.47)],state,':')
    text(2.5,3.17,labels[14],9)
    text(8.6,3.03,labels[13],9)
    box(9.7,4,2.25,.66,labels[15],'#E6EBE6')
    edge([(7.88,4.1),(8.54,4.1)],state,':')
    edge([(7.56,2.32),(9.7,2.32),(9.7,3.64)],state,':')
    for x,label,color,style in [(3.8,labels[17],water,'-'),(6,labels[18],decision,'--'),(8.1,labels[19],state,':')]:
        ax.plot([x-.6,x-.2],[.67,.67],color=color,ls=style,lw=1.7);text(x+.35,.67,label,10)
    output.parent.mkdir(parents=True,exist_ok=True)
    for extension in ('svg','pdf','png'):fig.savefig(output.with_suffix('.'+extension),dpi=200,bbox_inches='tight',facecolor='white')
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--language',choices=['en','zh-TW'],default='en')
    args=parser.parse_args();render(args.output,args.language)
