from __future__ import division
from collections import OrderedDict
import pandas as pd
import numpy as np
from scipy import ndimage as nd
from scipy.interpolate import UnivariateSpline as InterpSpline
import diviner as div

SV_LENGTH = 80

SV_NUM_SKIP_SAMPLE = 16
BBV_NUM_SKIP_SAMPLE = 16
SOLV_NUM_SKIP_SAMPLE = 16

class Flag(object):
    """Helper class to deal with control words or flags.

    Bit setting and checking methods are implemented.
    """
    def __init__(self, value = 0, dic = None):
        self.value = int(value)
        if dic:
            self.dic = dic
            self.set_members()
            
    def set_members(self):
        for flagname,val in self.dic.iteritems():
            # add the flagname and it's status, but cut off initial
            # qf_ from the name
            setattr(self, flagname, self.check_bit(val))
    def set_bit(self, bit):
        self.value |= bit
        self.set_members()
    def check_bit(self, bit):
        return self.value & bit != 0
    def clear_bit(self, bit):    
        self.value &= ~bit
        self.set_members()
    def __str__(self):
        # find longest key
        lwidth = 0
        for key in self.dic.keys():
            if len(key) > lwidth:
                lwidth = len(key)
        s = ''
        for key in self.dic:
            s += '{0} : {1}\n'.format(key.ljust(lwidth), 
                                     str(getattr(self,key)).rjust(6))
        return s
    def __call__(self):
        print(self.__str__())

class CalibFlag(Flag):
    flag_data=(
        #  Bit 0: Interpolation but one or more marker out of bounds
    	('interp_marker_oob', 0x00000001),
        #  Bit 1: Offsets and Gains from Nearest Marker used
    	('nearest_marker', 0x00000002),
        #  Bit 2: Same as bit 1, but nearest marker is out of bounds
    	('nearest_marker_oob', 0x00000004),
        #  Bit 3: Use constants for offsets and gains
    	('constants_only', 0x00000008),
    )
    flags = OrderedDict()
    for t in flag_data:
        flags[t[0]]=t[1]
    def __init__(self,value=0):
        super(CalibFlag,self).__init__(value,dic=self.flags)
            
class MiscFlag(Flag):
    flag_data=(
        #  Bit 0: Reserved for future use
    	('rfu0', 0x00000001),
    	('eclipse', 0x00000002),
    	('turn_on_transient', 0x00000004),  
    	('abnormal_instrument_state', 0x00000008),
    	('abnormal_instrument_temp_drift', 0x00000010),
    	('noise', 0x00000020),
    	('ch1_saturation', 0x00000040),
    	('moving', 0x00000080), 
    )
    # this convoluted way is necessary to keep the dictionary in order
    flags = OrderedDict()
    for t in flag_data:
        flags[t[0]]=t[1]
    def __init__(self,value=0):
        super(MiscFlag,self).__init__(value,dic=self.flags)

def plot_calib_data(df, c, det):
    """plot the area around calibration data in different colors"""
    cdet = get_cdet_frame(df, c, det)
    # # use sclk as index
    # cdet.set_index('sclk',inplace=True)
    # plot data in space orientation 
    cdet.counts[cdet.el_cmd==80].plot(style='ko')
    # plot bb counts in blue
    cdet.counts[cdet.el_cmd==0].plot(style='ro')
    # plot moving data in red
    return cdet.counts[is_moving(cdet)].plot(style='gx',markersize=15)

def get_cdet_frame(df,c,det):
    return df[(df.c==c) & (df.det==det)]

def get_spaceviews(df, moving=False):
    newdf = df[df.el_cmd==80]
    if not moving:
        newdf = get_non_moving_data(newdf)
    return newdf
    
def get_bbviews(df, moving=False):
    newdf = df[df.el_cmd==0]
    if not moving:
        newdf = get_non_moving_data(newdf)
    return newdf

def get_calib_data(df, moving=False):
    newdf = df[df.el_cmd.isin([80,0])]
    return newdf if moving else get_non_moving_data(newdf)
    
def is_moving(df):
    miscflags = MiscFlag()
    movingflag = miscflags.dic['moving']
    return df.qmi.astype(int) & movingflag !=0
    
def get_non_moving_data(df):
    """take dataframe and filter for moving flag"""
    return df[-(is_moving(df))]

def label_calibdata(cdet, calibdf, label):
    """This needs the index to be integer, time indices are not supported by nd.label"""
    # get a series with the size and index of the incoming dataframe
    calib_id = pd.Series(np.zeros_like(cdet.index), index=cdet.index)
    # set the value to 1 (or True) where the calibdf has an index
    calib_id[calibdf.index] = 1
    # label the calib_id series and add to the incoming dataframe
    cdet[label] = nd.label(calib_id)[0]
    # cdet[label] = 0
    # calib_id = cdet[label]
    # calib_id[calibdf.index] = 1
    # cdet[label] = nd.label(calib_id)[0]
    
def get_offset_use_limits(grouped):
    # for now, use the end of 2nd spaceview as end of application time
    # for mean value of set of spaceviews
    return [g.index[-1] for i,g in grouped.counts if not i==0][1::2]

def add_offset_col(df, grouped):
    index = get_offset_use_limits
    data = grouped.coutns.mean()[[2,4,6,8]].values
    offsets = pd.Series(data, index=index)
    df['offsets'] = offsets.reindex_like(cdet, method='bfill')

def get_grouped(cdet):
    bbviews = get_bbviews(cdet)
    label_calibdata(cdet, bbviews, 'bbviews')
    grouped_bb = cdet.groupby('bbviews')
    spaceviews = get_spaceviews(cdet)
    label_calibdata(cdet, spaceviews, 'spaceviews')
    grouped_sv = cdet.groupby('spaceviews')
    return grouped_bb, grouped_sv

def get_bb_means(grouped_bb):
    return grouped_bb.counts.mean()[1:]

def get_bb2_col(df):
    # get the bb2 temps without the nans
    bb2temps = df.bb_2_temp.dropna()
    #create interpolater function by interpolating over bb2temps.index (needs
    # to be integer!) and its values
    s = InterpSpline(bb2temps.index.values, bb2temps.values, k=1)
    return pd.Series(s(df.index), index=df.index)

def calc_gain():
    pass

class DivCalib(object):
    """docstring for DivCalib"""
    def __init__(self, df):
        self.df = df
        self.dfsmall = df[['c','det','counts','bb_1_temp','bb_2_temp','el_cmd','az_cmd',
                      'year','month','date','hour','minute','second','qmi','clat','clon',
                      'scalt']]
        self.timed = div.index_by_time(self.dfsmall)
        # self.timed.set_index(['c','det',self.timed.index], inplace=True)
        # self.timed.index.names = ['c','det','time']
        # loading conversion table indexed in T*100 (for resolution)
        self.t2nrad = pd.load('Ttimes100_to_Radiance.df')
        # get interpolated bb temps
        self.add_bb_cols()
        # get the normalized radiance
        self.get_nrad()
    def add_bb_cols(self):
        df = self.timed
        # take temperature measurements of ch1/det1
        # (only way to guarantee unique T-measurements)
        bb2temps = df.bb_2_temp[(df.c==1) & (df.det==1)].dropna()
        bb1temps = df.bb_1_temp[(df.c==1) & (df.det==1)].dropna()
        all_times = df.index.unique()
        for bbtemp in [bb1temps,bb2temps]:
            # converting the time series to floats for interpolation
            ind = bbtemp.index.values.astype('float64')
            s = InterpSpline(ind, bbtemp, s=0.05, k=3)
            # adding interpolated data to the timed dataframe
            df[bbtemp.name + '_interp'] = pd.Series(s(all_times.astype('float64')),
                                                      index=all_times)
                                     
    def get_nrad(self):
        bbv = get_bbviews(self.timed)
        bbv['nrad'] = 0.0
        # create dictionary to look up the right temperature for different channels
        l = [(i,'bb_1_temp_interp') for i in range(3,7)]
        l2 = [(i,'bb_2_temp_interp') for i in range(7,10)]
        d = dict(l+l2)
        for ch in range(3,10):
            # rounding to 2 digits and * 100 to lookup the values that have been 
            # indexed by T*100 to enable float value table lookup
            bbv.nrad[bbv.c==ch] = \
                self.t2nrad.ix[bbv[d[ch]][bbv.c==ch].round(2)*100, 
                               ch].astype('float')
        self.bbv = bbv
        
def thermal_alternative():
    """using the offset of visual channels???"""
    pass
        
def thermal_nearest(node, tmnearest):
    """Calibrate for nearest node only.
    
    If only one calibration marker is available, no interpolation is done and 
    the gain and offset will be determined only with one measurement.
    
    Input
    =====
    node: Datanode container
    tmnearest: ThermalMarkerNode container
    """
    counts = node.counts
    offset = (tmnearest.offset_left_SV + tmnearest.offset_right_SV)/2.0
    gain = tmnearest.gain
    radiance = (counts - offset) * gain
    radiance = rconverttable.convertR(radiance, chan, det)
    tb = rbbtable.TB(radiance, chan, det)
    radiance *= config.CalRadConstant(chan)
   
def calc_gain(chan, det, thermal_marker_node):
    numerator = -1 * thermal_marker_node.calcRBB(chan,det)
    denominator = (thermal_marker_node.calc_offset_leftSV(chan, det) + 
                   thermal_marker_node.calc_offset_rightSV(chan,det)) / 2.0
                   # calc_CBB is just the mean of counts in BB view
    denominator -= thermal_marker_node.calc_CBB(chan, det)
    return numerator/denominator
    
