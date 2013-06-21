# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>
from __future__ import division, print_function
from matplotlib.pyplot import show, rcParams, subplots
from diviner import file_utils as fu
from diviner import calib
import pandas as pd
from diviner import file_utils as fu
from datetime import timedelta

rcParams['figure.figsize'] = (14, 10)


class HotOrbits(object):
    """docstring for HotOrbits"""
    savepath = '/Users/maye/Dropbox/DDocuments/DIVINER/calib/hot_orbits/jpl_meeting/'

    def __init__(self, ch2study, df, title_prefix='', rad_corr=True, 
                 do_negative_corr=False):
        super(HotOrbits, self).__init__()
        self.ch2study = ch2study
        self.df = df
        self.title_prefix = title_prefix
        self.rad_corr = rad_corr
        self.do_negative_corr = do_negative_corr
        
        # my calibration
        c = calib.Calibrator(df, do_rad_corr=rad_corr, 
                                 do_negative_corr=do_negative_corr)
        c.calibrate()
        self.c = c
        
    def set_ch2study(self, ch):
        ch2study = ch
        self.ch2study = ch
        # get only Tb
        Tb_all = calib.get_data_columns(self.c.Tb)
        Tb = Tb_all.filter(regex=ch2study + '_')
        
        # make all detectors integer numbers
        Tb = Tb.rename(columns=lambda x: int(x[3:]))

        # cut off first 30 minutes for boundary effects
        t0 = Tb.index[0]
        Tb = Tb.ix[(t0 + timedelta(minutes=30)):]
               
        self.Tb = Tb.resample('10s')
        self.chmedian = self.Tb.apply(lambda x: x - x.median(), axis=1)
        self.chmean = self.Tb.apply(lambda x: x - x.mean(), axis=1)
        
    def plot_detectors(self, det_list=[1,11,21]):
        fig, ax = subplots()

        self.Tb[det_list].plot(ax=ax)
        ax.legend()
        ax.set_ylabel('Tb [K]')
        ax.set_xlabel('Time [UTC]')
        # ax.set_ylim(ymin=-100,ymax=400)
        corr_string = self.get_corr_string()
        titlestr = '{0} Tb Det 01 11 21 _ {1}'.format(self.ch2study, corr_string)
        ax.set_title(' '.join([self.title_prefix, titlestr]))
        savestring = self.savepath + '_'.join(titlestr.split()) + '.png' 
        print(savestring)
        fig.savefig(savestring, dpi=200)

    def get_save_string(self):
        corr_string = self.get_corr_string()
        titlestr = '{0} Tb Det 01 11 21 _ {1}'.format(self.ch2study, corr_string)
        savestring = self.savepath + '_'.join(titlestr.split()) + '.png'
        return savestring

    def plot_raw(self, ):
        df = self.df
        ch2study = self.ch2study
        figure()
        col = self.ch2study+'_11'
        # df[col].plot(style='k.', markersize=2, )
        plot(df[col].index, df[col], 'k.', markersize=2)
        # df[df.is_spaceview][col].plot(style='b.', markersize=4)
        plot(df[df.is_spaceview][col].index, 
                df[df.is_spaceview][col], 
                'b.', markersize=4)
        # choffsets[self.ch2study+'_11'].plot(style='b.', markersize=2, )
        plot(df[df.is_bbview][col].index,
                df[df.is_bbview][col], 
                'r.', markersize=2, )
        # chbbs[self.ch2study+'_11'].plot(style='r.', markersize=2, )
        # if len(df[df.is_stview]) is not 0:
        #     df[df.is_stview][col].plot(style='c.', markersize=5, )
        titlestr = ch2study + ' raw  plus marked calib views'
        title(' '.join([self.title_prefix, titlestr]))
        ylabel('Counts')
        xlabel('Time [UTC')
        savefig(self.savepath + '_'.join(titlestr.split()) + '.png')
    
        
    def get_corr_string(self):
        if self.rad_corr:
            if self.do_negative_corr:
                corr_string = 'INV_corrected'
            else:
                corr_string = 'corrected'
        else:
            corr_string = 'uncorrected'
        return corr_string
        
    def plot_lips(self, kind='mean', separate=True):

        fig, ax = subplots()
        
        if kind == 'median':
            df = self.chmedian
        elif kind == 'mean':
            df = self.chmean

        if separate:
            for i in range(1, 12):
                df[i].plot(style='r', ax=ax)
            for i in range(12, 22):
                df[i].plot(style='g', ax=ax)
            df[21].plot(style='k', ax=ax)
        else:
            df.plot(ax=ax)
        ax.legend(ncol=5,loc='lower right')
        # ax.set_ylim(ymin=-80,ymax=60)

        corr_string = self.get_corr_string()
        titlestr = self.ch2study + \
            ' Tb Deviations from {0} detector sides sorted_{1}'.format(kind, corr_string)
        ax.set_title(' '.join([self.title_prefix, titlestr]))
        savestring = self.savepath + '_'.join(titlestr.split()) + '.png'
        print(savestring)
        fig.savefig(savestring, dpi=200)
            
    def imshow(self):
        figure(figsize=(21,3))
        imshow(self.Tb.values.T, interpolation='none', aspect='auto')  
        colorbar(orientation='horizontal')
        titlestr = self.ch2study + ' channel image plot'
        title(' '.join([self.title_prefix, titlestr]))
        savefig(self.savepath + '_'.join(titlestr.split()) + '.png')
        
    def plot_max_deviation_det(self):
        figure()
        self.chmedian.idxmax(axis=1).plot(style='.')
        xlabel('Time [UTC]')
        ylabel('Detector number')
        tstr = 'Which detector shows the largest deviation from the median'
        title(' '.join([self.title_prefix,tstr]))
        savefig(self.savepath + '_'.join(tstr.split()) + '.png')
        
    def plot_kde(self):
        self.Tb.plot(kind='kde')
        legend()
        tstr = 'Detector KDEs'
        title(' '.join([self.title_prefix, tstr]))
        savefig(self.savepath + '_'.join(tstr.split()) + '.png')
        
    def plot_gains_interp(self):
        self.c.gains_interp.plot(style='*')
        savefig(self.savepath + 'gains_interp.png')

class HotOrbitsDivData(HotOrbits):
    def __init__(self, ch2study, Tb, title_prefix=""):
        self.ch2study = ch2study
        self.Tb = Tb
        self.chmedian = Tb.apply(lambda x: x - x.median(), axis=1)
        self.chmean = Tb.apply(lambda x: x - x.mean(), axis=1)
        self.savepath = self.savepath + 'divdata_'
        self.title_prefix = title_prefix
####
### start of script
####

# Channel to study:
ch2study = 'a5'

# get L1A data
timestr = '20110402'
offset = 4
pump = fu.Div247DataPump(timestr)
df = pump.get_n_hours_from_t(6, offset)

hotorbits_corr = HotOrbits(ch2study, df, timestr + str(offset), rad_corr=True)
hotorbits_uncorr = HotOrbits(ch2study, df, timestr + str(offset), rad_corr=False)
hotorbits_negcorr = HotOrbits(ch2study, df, timestr + str(offset), rad_corr=True,
                              do_negative_corr=True)
                        
detectors = ['a3','a4','a5','a6','b1','b2','b3']
# detectors = ['b3']
for ch in detectors:
    print("Doing", ch)
    hotorbits_corr.set_ch2study(ch)
    hotorbits_uncorr.set_ch2study(ch)
    hotorbits_negcorr.set_ch2study(ch)
    hotorbits_corr.plot_detectors()
    hotorbits_uncorr.plot_detectors()
    hotorbits_negcorr.plot_detectors()
# hotorbits.plot_raw()
# hotorbits.imshow()
    hotorbits_corr.plot_lips(kind='mean', separate=True)
    hotorbits_uncorr.plot_lips(kind='mean', separate=True)
    hotorbits_negcorr.plot_lips(kind='mean', separate=True)
    
# hotorbits.plot_max_deviation_det()
# hotorbits.plot_kde()

# hotorbits.plot_gains_interp()

# statistics for each channel
# hotorbits.Tb.boxplot()

# or this simple statistic?
# Tb.std()


# divdata = pd.io.parsers.read_csv('/Users/maye/data/diviner/hot_orbit_ch9.txt', sep=r'\s*', names=['year', 'month', 'date', 'hour', 'minute', 'second', 'det', 'tb', 'qca'])
# 
# df = fu.index_by_time(divdata)
# print("\Index for divdata:", df.index)
# print("\nqca: ",df.qca.unique())
# 
# df = df.reset_index()
# df = df.pivot(index='index', columns='det', values='tb')
# df.columns = range(1,22)
# divhotorbits = HotOrbitsDivData(ch2study, df, timestr + str(offset) + '_divdata')
# divhotorbits.plot_detectors()
# divhotorbits.imshow()
# divhotorbits.plot_max_deviation_det()
# divhotorbits.plot_kde()

#show()