'''
Nash Equilibria on (Un-)Stable Networks

2020
Anton Badev
anton.badev@gmail.com

Plots the simulations generated by modelFit.py
Compare simulations from the model with the data

Input files:
    estimation_top8_100plus.data
    modelFit.data
Output files:
    table_fit.tex
    table_fit_mixing.tex
Note output in texdir
'''


import os,sys,csv,multiprocessing,functools
import time
import numpy as np
import pandas as pd
import scipy.io as sio
import pickle
from tqdm import tqdm

from libsetups import state2pickle
from libsetups import setupdirs
from libposteriors import posteriorStats
from libnets import netStats
from libnets import stateStats2
from libnets import homophily
from libnets import mixingMat
from libnets import nodeStats




def weighted_average_bygroup(dfin,data_col,weight_col,by_col):
    df=dfin.copy()
    df['_data_times_weight'] = df[data_col]*df[weight_col]#/float((df[weight_col].sum())
    df['_weight_where_notnull'] = df[weight_col]*pd.notnull(df[data_col])
    g = df.groupby(by_col)
    result = g['_data_times_weight'].sum() / g['_weight_where_notnull'].sum()
    del df['_data_times_weight'], df['_weight_where_notnull']
    return result

def weighted_average(df,data_col,weight_col):
    result = np.average(df[data_col].to_numpy(float),axis=None,weights=df[weight_col].to_numpy(float))
    #result = df[data_col]*df[weight_col].astype(float)).sum()/float(df[weight_col].sum())
    return result

def weighted_median(df,data_col,weights):
    result = np.average(df[data_col].to_numpy(float),axis=None,weights=df[weight_col].to_numpy(float))
    #result = df[data_col]*df[weight_col].astype(float)).sum()/float(df[weight_col].sum())
    return result

def main():

    [systime0,pyfilename,pyfiledir,homedir,currentdir,scratchdir,hostname,sysname] = setupdirs()
    modelfitData= '/../modelFit.data'

    with open(scratchdir+modelfitData, 'rb') as filehandle:
        simdata=pickle.load(filehandle)

    texdir   = currentdir + '/../../TeX/'
    texfile  = 'table_fit.tex'
    texfile2 = 'table_fit_mixing.tex'

    ## Load data.
    with open(currentdir+'/../../Data/estimation_top8_100plus.data', 'rb') as filehandle:
        [num_nets, size_nets, attr, data_a, data_g]=pickle.load(filehandle)

    nodestats=[None]*num_nets
    ntot=int(0)
    for jnet,simnet in enumerate(simdata):
        AA=simnet[0]
        GG=simnet[1]
        nsim=len(AA)
        n=len(AA[0])
        ntot=ntot+n
        prev=np.zeros(nsim)
        density=np.zeros(nsim)
        avgDeg=np.zeros(nsim)
        minDeg=np.zeros(nsim)
        maxDeg=np.zeros(nsim)
        AGA=np.zeros(nsim)
        IAGIA=np.zeros(nsim)
        tri=np.zeros(nsim)
        twolinksonly=np.zeros(nsim)
        twolinksonly2=np.zeros(nsim)
        HI=np.zeros(nsim)
        CHI=np.zeros(nsim)
        FSI=np.zeros(nsim)
        nn=np.zeros(nsim)
        ns=np.zeros(nsim)
        sn=np.zeros(nsim)
        ss=np.zeros(nsim)
        nodestats[jnet]=nodeStats(GG[0],n,True)
        for s in range(nsim):
            A=AA[s] #subdimensional array
            G=GG[s] #subdimensional array
            [prev[s],
             density[s],
             avgDeg[s],
             minDeg[s],
             maxDeg[s],
             AGA[s],
             IAGIA[s],
             tri[s],
             twolinksonly[s],
             twolinksonly2[s],
             stateStatsLabels]=stateStats2(G,A,len(A))
            [HI[s],CHI[s],FSI[s]]=homophily(G,A,n,True)
            [nn[s],ns[s],sn[s],ss[s]] = list((mixingMat(G,A.astype(int),n,2).ravel('C')).astype(float))

        jnetstats=pd.DataFrame(data=np.column_stack([prev,density,avgDeg,minDeg,maxDeg,AGA,IAGIA,tri,twolinksonly,twolinksonly2,HI,CHI,FSI,nn,ns,sn,ss]),
                    dtype=float,
                    columns=['prev','density','avgDeg','minDeg','maxDeg','AGA','IAGIA','tri','twolinks','twolinks2','HI','CHI','FSI','nn','ns','sn','ss'])
        jnetstats['netid']=(jnet+1)#.astype(int)
        jnetstats['netsize']=n#.astype(int)
        jnetstats['sim']=list(range(nsim))

        if jnet==0:
            stats=jnetstats
        else:
            stats=pd.concat([stats,jnetstats])

    allstats_model=stats[stats.sim>0].groupby('netid').describe()
    allstats_data =stats[stats.sim==0].groupby('netid').describe()
    allstats = allstats_data.append(allstats_model, ignore_index=True) #top data, botom model
    
    median_model=stats[stats.sim>0].groupby('netid').median()
    median_model['netsize']=np.asarray(size_nets,dtype=int)
    median_data=stats[stats.sim==0].groupby('netid').median()
    median_data['netsize']=np.asarray(size_nets,dtype=int)
    mean_model=stats[stats.sim>0].groupby('netid').mean()
    mean_model['netsize']=np.asarray(size_nets,dtype=int)
    mean_data=stats[stats.sim==0].groupby('netid').mean()
    mean_data['netsize']=np.asarray(size_nets,dtype=int)


    del AA, GG, prev, density, avgDeg, minDeg, maxDeg, AGA, IAGIA, tri

    varlist=['prev', 'density', 'avgDeg', 'minDeg', 'maxDeg', 'AGA', 'IAGIA', 'twolinks', 'tri','HI','CHI','FSI']
    varlabels=['Prevalence','Density','Avg degree','Min degree','Max degree',
               '$a_ig_{ij}a_j/n$','$(1-a_i)g_{ij}(1-a_j)/n$','Two-paths$/n$','Triangles$/n$','HI','CHI','FSI']
    statsdata=np.zeros(len(varlist))
    statsmodel=np.zeros(len(varlist))
    for j,var in enumerate(varlist):
        statsdata[j]=weighted_average(stats[stats.sim==0],var,'netsize')
        statsmodel[j]=weighted_average(stats[stats.sim>0],var,'netsize')

    meddata =np.zeros(len(varlist))
    medmodel=np.zeros(len(varlist))
    for j,var in enumerate(varlist):
        meddata[j]=weighted_average(median_data,var,'netsize')
        medmodel[j]=weighted_average(median_model,var,'netsize')
    
    
    table_fit=''
    for j in range(9):
        texline= varlabels[j].rjust(24, ' ')
        texline = f'{texline} & {statsmodel[j]:5.3f} ({medmodel[j]:5.3f}) & {statsdata[j]:5.3f} '
        table_fit=table_fit + texline + r' \\' + ' \n'
            
        table_mixing=''
    for j in range(9,len(varlist)):
        texline= varlabels[j].rjust(24, ' ')
        texline = f'{texline} & {statsmodel[j]:5.3f} ({medmodel[j]:5.3f}) & {statsdata[j]:5.3f} '
        table_mixing=table_mixing + texline + r' \\' + ' \n'

    texsignature=f'% tex created by {pyfilename}.py \n'
    texheader = r'''
\begin{table}[t]
\caption{Model fit}
\label{table:fit}
\begin{center}
\begin{tabular}{lcc}
\hline \hline
\multicolumn{3}{c}{\textit{Selected moments}} \\
    Moment & Model & Data \\ \hline 
'''
    texmid = r'''
\\
\multicolumn{3}{c}{\textit{Mixing patterns}} \\ 
'''
    texfooter = r'''
\hline \\
\end{tabular}
\end{center}

\fignotetitle{Note:} 
\fignotetext{Columns Data and Model compare selected moments of the estimation sample with those of synthetic data 
generated by the estimated model. For the latter mean and median are reported (median in parentheses). 
Two-paths is defined as $\sum_{i>j} g_{ij}g_{il}(1-g_{il})$. Triangles is defined as $\sum_{i>j>l}g_{ij}g_{il}g_{il}$
For details on computing homophily indices see \cite{CurrariniJacksonPin2010} Definitions 1 and 2 in the supplemental appendix.}
\end{table} 
'''
    
    texcontent = texsignature + texheader + table_fit + texmid + table_mixing + texfooter
    with open(texdir+texfile,'w') as f:
        f.write(texcontent)


    
    #MIXING MAT
    nn_data  =weighted_average(stats[stats.sim==0],'nn','netsize')
    nn_model =weighted_average(stats[stats.sim>0],'nn','netsize')
    ns_data  =weighted_average(stats[stats.sim==0],'ns','netsize')
    ns_model =weighted_average(stats[stats.sim>0],'ns','netsize')
    sn_data  =weighted_average(stats[stats.sim==0],'sn','netsize')
    sn_model =weighted_average(stats[stats.sim>0],'sn','netsize')
    ss_data  =weighted_average(stats[stats.sim==0],'ss','netsize')
    ss_model =weighted_average(stats[stats.sim>0],'ss','netsize')
    
    row1=r'''& Smoker   & \textbf{'''+ f'{100*ss_model/(ss_model+sn_model):4.0f}\% ({ss_model:4.1f})' + r'''}''' 
    row1=row1+ f' & {100*sn_model/(ss_model+sn_model):4.0f}\% ({sn_model:4.1f})'
    row1=row1+ r''' & \textbf{'''+ f'{100*ss_data/(ss_data+sn_data):4.0f}\% ({ss_data:4.1f})' + r'''}''' 
    row1=row1+ f' & {100*sn_data/(ss_data+sn_data):4.0f}\% ({sn_data:4.1f})'
    row2=f' & Nonsmoker   & {100*ns_model/(ns_model+nn_model):4.0f}\% ({ns_model:4.1f})'
    row2=row2+ r'''& \textbf{''' + f' {100*nn_model/(ns_model+nn_model):4.0f}\% ({nn_model:4.1f})' + r'''}''' 
    row2=row2+ f' & {100*ns_data/(ns_data+nn_data):4.0f}\% ({ns_data:4.1f})'
    row2=row2+ r''' & \textbf{'''+ f' {100*nn_data/(ns_data+nn_data):4.0f}\% ({nn_data:4.1f})'+r'''}''' 
    #
    #  & Smoker     & \textbf{77\% (53.2)}  &  23\% (16.1)           & \textbf{77\% (52.8)}  &  23\% (15.5)          \\
    #  & Nonsmoker  & 44\% (16.1)           & \textbf{66\% (20.8)}   & 41\% (15.5)           & \textbf{59\% (22.8)}\\  \cline{2-6}
    
    
    
    texheader = r'''
\begin{table}[t]
\caption{Fit mixing matrix (model left, data right)}
\label{table:fit_mixing}
\centering
\begin{footnotesize}
\begin{tabular}{llcccc}
%\cmidrule{2-4} \morecmidrules \cmidrule{2-4}
  &  & \multicolumn{2}{c}{\axislabel{Nominee}}                                 & \multicolumn{2}{c}{\axislabel{Nominee}} \\
  \multirow{5}{*}{\rotatebox[origin=c]{90}{\axislabel{Nominator}}}
  &            & Smoker               & Nonsmoker                      & Smoker               & Nonsmoker           \\\cmidrule{2-6}
'''
    
    texfooter = r'''
\\
\cmidrule{2-6}
\end{tabular}

\end{footnotesize}
%\fignotetitle{Source:} \fignotetext{The National Longitudinal Study of Adolescent Health (Add Health) - Wave I, 1994-95 school year (Estimation sample: $14$ schools, $1,125$ students, $21\%$ smokers).}
\end{table}
'''
    
    texcontent = texsignature + texheader + row1 +r'''\\'''+ ' \n'+row2 + texfooter
    with open(texdir+texfile2,'w') as f:
        f.write(texcontent)
         
if __name__ == '__main__':
    main()

