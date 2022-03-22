import math
import copy

import numpy as np
from scipy import signal
from scipy import integrate

import heapq as hq
from numba import cuda,jit

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from time import perf_counter


@jit(nopython=True)
def dist_func(x, y):
    return (x - y)**2


@jit(nopython=True)
def _updateStwm(querySequence,stwmD,stwmI,sampling,current_value):
    Q = querySequence
    D = stwmD
    I = stwmI
    D[:, 1:] = D[:, :-1]
    I[:, 1:] = I[:, :-1]
    m = len(D)
    N = sampling
    st = current_value

    D[0, 0] = dist_func(Q[0], st)
    I[0, 0] = N

    for i in range(1, m):
        D[i, 0] = dist_func(Q[i], st) + min(D[i - 1, 1], D[i, 1], D[i - 1, 0])

        Min = min(D[i - 1, 1], D[i, 1], D[i - 1, 0])
        if Min == D[i - 1, 1]:
            I[i, 0] = I[i - 1, 1]
        elif Min == D[i, 1]:
            I[i, 0] = I[i, 1]
        elif Min == D[i - 1, 0]:
            I[i, 0] = I[i - 1, 0]

    return D, I


class Signal():
    matchedSequenceCandidateArray = []
    matchedSequenceCandidateArrayTime = []
    matchedSequence = []
    matchedSequenceTime = []
    stwmDCandidateArray = []
    dtwDistanceSequence = []
    adjacentSequence = []
    adjacentSequence2 = []
    adjacentSequenceTime = []
    adjacentSequenceTime2 = []
    adjacentSequenceTime3 = []
    count = 0
    countSingleSequence = 0
    localMaximum=None
    localMinimun=None
    frequence = None


    def __init__(self, fullSequencePath = None, querySequencePath = None, downsample = 1,threshold = 1):
        self.querySequence = np.loadtxt(querySequencePath)
        if len(self.querySequence)>100:
            self.querySequence = signal.savgol_filter(signal.resample(self.querySequence,int(100/downsample)),2,1)
        else:
            self.querySequence = signal.savgol_filter(signal.resample(self.querySequence,int(len(self.querySequence)/downsample)),2,1)
        self.fullSequence = np.loadtxt(fullSequencePath)[::downsample]
        self.querySequenceLength = len(self.querySequence)
        self.presentSequenceLength = int(2000/downsample)
        self.presentSequence = np.zeros(self.presentSequenceLength)
        self.presentSequenceTime = np.zeros(self.presentSequenceLength)
        self.stwmD = np.zeros([self.querySequenceLength,self.presentSequenceLength]);self.stwmD[:,0] = np.inf
        self.stwmI = np.zeros([self.querySequenceLength,self.presentSequenceLength])
        self.threshold = threshold


    def updateSequence(self):
        global N
        self.st = self.fullSequence[N][1]
        self.presentSequence[1:] = self.presentSequence[:-1]
        self.presentSequence[0] = self.st

        self.stTime = self.fullSequence[N][0]
        self.presentSequenceTime[1:] = self.presentSequenceTime[:-1]
        self.presentSequenceTime[0] = self.stTime


    def updateStwm(self):
        global N
        self.stwmD,self.stwmI = _updateStwm(self.querySequence,self.stwmD,self.stwmI,N,self.st)


    def getMatchedSequence(self, getAdjacentSequence = False, findSpritzermode = False):
        global N
        D = self.stwmD
        I = self.stwmI

        # Start append candidate sequences
        if D[-1, 0] <= self.threshold:
            if D[-1, 1] > self.threshold:
                self.stwmDCandidateArray = []
                self.matchedSequenceCandidateArray = []
                self.matchedSequenceCandidateArrayTime = []
            self.stwmDCandidateArray.append(D[-1, 0])
            self.matchedSequenceCandidate = self.presentSequence[0:int(N - I[-1, 0]) + 1]
            self.matchedSequenceCandidateTime = self.presentSequenceTime[0:int(N - I[-1, 0]) + 1]
            self.matchedSequenceCandidateArray.append(copy.copy(self.matchedSequenceCandidate))
            self.matchedSequenceCandidateArrayTime.append(copy.copy(self.matchedSequenceCandidateTime))


        if D[-1, 0] > self.threshold:
            # end append candidate sequences
            if D[-1, 1] <= self.threshold:
                if findSpritzermode == True:
                    self.stwmDCandidateArray = self.stwmDCandidateArray[::-1]
                    # local_min_index = len(self.stwmDCandidateArray) - 1 - self.stwmDCandidateArray.index(min(self.stwmDCandidateArray[::-1]))
                    localMinIndex = self.stwmDCandidateArray.index(min(self.stwmDCandidateArray))

                    if len(self.matchedSequenceCandidateArray[localMinIndex]) < 2.5*self.querySequenceLength:
                        self.matchedSequence = self.matchedSequenceCandidateArray[localMinIndex]
                        self.matchedSequenceTime = self.matchedSequenceCandidateArrayTime[localMinIndex]

                        self.count += 1
                        self.localMinimun = min(self.matchedSequence)
                        self.localMaximum = max(self.matchedSequence)
                        self.frequence = 1/(self.matchedSequenceTime[0] - self.matchedSequenceTime[-1])

                        self.stwmDCandidateArray = []
                        self.matchedSequenceCandidateArray = []
                        self.matchedSequenceCandidateArrayTime = []

                else:
                    self.stwmDCandidateArray = self.stwmDCandidateArray[::-1]
                    # local_min_index = len(self.stwmDCandidateArray) - 1 - self.stwmDCandidateArray.index(min(self.stwmDCandidateArray[::-1]))
                    localMinIndex = self.stwmDCandidateArray.index(min(self.stwmDCandidateArray))
                    self.matchedSequence = self.matchedSequenceCandidateArray[localMinIndex]
                    self.matchedSequenceTime = self.matchedSequenceCandidateArrayTime[localMinIndex]

                    self.count += 1
                    self.localMinimun = min(self.matchedSequence)
                    self.localMaximum = max(self.matchedSequence)
                    self.frequence = 1 / (self.matchedSequenceTime[0] - self.matchedSequenceTime[-1])


                    self.stwmDCandidateArray = []
                    self.matchedSequenceCandidateArray = []
                    self.matchedSequenceCandidateArrayTime = []

                if getAdjacentSequence == True:
                    self.adjacentSequenceTime2.append(copy.copy(list(self.matchedSequenceTime[::-1])))
                    index1 = int(np.argwhere(self.presentSequenceTime == self.adjacentSequenceTime2[-1][-1]))
                    index2 = int(np.argwhere(self.presentSequenceTime == self.adjacentSequenceTime2[0][0]))+1
                    self.adjacentSequence2 = copy.copy(self.presentSequence[index1:index2][::-1])
                    self.adjacentSequence = self.adjacentSequence2
                    self.adjacentSequenceTime3 =copy.copy(self.presentSequenceTime[index1:index2][::-1])
                    self.adjacentSequenceTime = self.adjacentSequenceTime3
                    self.countSingleSequence += 1





            if D[-1, 1] > self.threshold:
                self.stwmDCandidateArray = []
                self.matchedSequenceCandidateArray = []
                self.matchedSequenceCandidateArrayTime = []

                if getAdjacentSequence == True:
                    if len(self.matchedSequenceTime) != 0:
                        if self.stTime > (self.matchedSequenceTime[0]+4*(self.matchedSequenceTime[0]-self.matchedSequenceTime[-1])):

                            self.adjacentSequence2 = []
                            self.adjacentSequenceTime3 = []
                            self.adjacentSequenceTime2 = []
                            self.countSingleSequence = 0



    def setPlot1(self,title = None,pen = "white"):

        self.tempData = []
        self.tempDataTime = []
        self.p1 = win.addPlot(title=title)
        self.curve1 = self.p1.plot(pen = pen)


    def setPlot2(self,title = None,pen = "white"):
        self.p2 = win.addPlot(title=title)
        self.curve2 = self.p2.plot(pen = pen)

    def setPlot3(self, title=None, pen="white"):
        self.p3 = win.addPlot(title=title)
        self.curve3 = self.p3.plot(pen=pen)


    def setPlot4(self, title=None, pen="white"):
        self.tempData4 = []
        self.tempDataTime4 = []
        self.p4 = win.addPlot(title=title)
        self.curve4 = self.p4.plot(pen=pen)
        self.curve4_1 = self.p4.plot(pen="red")
        self.p4.setYRange(0.1*self.threshold,1.9*self.threshold)


    def updatePlot1(self):
        global N
        if N < self.presentSequenceLength:
            self.tempDataTime.append(self.stTime)
            self.tempData.append(self.st)
            self.curve1.setData(x = self.tempDataTime, y = self.tempData)
        else:
            self.curve1.setData(x = self.presentSequenceTime[::-1], y = self.presentSequence[::-1])


    def updatePlot2(self):
        self.curve2.setData(x = self.matchedSequenceTime[::-1], y = self.matchedSequence[::-1])


    def updatePlot3(self):
        self.curve3.setData(x = self.adjacentSequenceTime, y = self.adjacentSequence)


    def updatePlot4(self):
        if N < self.presentSequenceLength:
            self.tempDataTime4.append(self.stTime)
            self.tempData4.append(self.stwmD[-1,0])
            self.curve4.setData(x = self.tempDataTime4, y = self.tempData4)
            self.curve4_1.setData(x = self.tempDataTime4,y = [self.threshold]*int(N/15+1))
        else:
            self.curve4.setData(x=self.presentSequenceTime[::-1], y=self.stwmD[-1][::-1])
            self.curve4_1.setData(x = self.presentSequenceTime[::-1], y = [self.threshold]* self.presentSequenceLength)



    def updateData(self,getAdjacentSequence = False,findSpritzermode = False):
        self.updateSequence()
        self.updateStwm()
        self.getMatchedSequence(getAdjacentSequence=getAdjacentSequence, findSpritzermode = findSpritzermode)


class Power():

    def __init__(self,signal1,signal2):
        self.presentSequenceLength = len(signal1.presentSequence)
        self.presentSequence = np.zeros(self.presentSequenceLength)
        self.presentSequenceEnergy = np.zeros(self.presentSequenceLength)
        self.presentSequenceEnergySum = np.zeros(self.presentSequenceLength)


    def updateSequence(self,signal1,signal2):
        global N
        self.st = signal1.st * signal2.st
        self.presentSequence[1:] = self.presentSequence[:-1]
        self.presentSequence[0] = self.st
        self.presentSequenceTime = signal1.presentSequenceTime
        self.stTime = self.presentSequenceTime[0]


    def calculateEnergy(self):
        global N
        if N == 0:
            self.stEnergy = 0
            self.stEnergySum = self.stEnergy
        else:
            self.stEnergy = integrate.trapz(self.presentSequence[:2][::-1], self.presentSequenceTime[:2][::-1])
            self.stEnergySum = self.stEnergySum + self.stEnergy

        self.presentSequenceEnergySum[1:] = self.presentSequenceEnergySum[:-1]
        self.presentSequenceEnergySum[0] = self.stEnergySum

        self.presentSequenceEnergy[1:] = self.presentSequenceEnergy[:-1]
        self.presentSequenceEnergy[0] = self.stEnergy


    def setPlot1(self,title = None,pen = "white"):
        self.tempData = []
        self.tempDataTime = []
        self.p1 = win.addPlot(title=title)
        self.curve1 = self.p1.plot(pen = pen)


    def setPlot2(self, title=None, pen="white"):
        self.tempData2 = []
        self.p2 = win.addPlot(title=title)
        self.curve2 = self.p2.plot(pen=pen)


    def setPlot3(self, title=None, pen="white"):
        self.tempData3 = []
        self.p3 = win.addPlot(title=title)
        self.curve3 = self.p3.plot(pen=pen)


    def updatePlot1(self):
        global N
        if N < self.presentSequenceLength:
            self.tempDataTime.append(self.stTime)
            self.tempData.append(self.st)
            self.curve1.setData(x=self.tempDataTime, y=self.tempData)
        else:
            self.curve1.setData(x=self.presentSequenceTime[::-1], y=self.presentSequence[::-1])


    def updatePlot2(self):
        if N < self.presentSequenceLength:
            self.tempData2.append(self.stEnergy)
            self.curve2.setData(x = self.tempDataTime, y = self.tempData2)
        else:
            self.curve2.setData(x = self.presentSequenceTime[::-1], y = self.presentSequenceEnergy[::-1])


    def updatePlot3(self):
        if N < self.presentSequenceLength:
            self.tempData3.append(self.stEnergySum)
            self.curve3.setData(x = self.tempDataTime, y = self.tempData3)
        else:
            self.curve3.setData(x = self.presentSequenceTime[::-1], y = self.presentSequenceEnergySum[::-1])

cmtAndPulseSequence = []
cmtAndPulseSequenceTime = []
globalFrequenz = 0

def getCmtAndPluse(cmt,pulse):
    global cmtAndPulseSequence, cmtAndPulseSequenceTime, globalFrequenz
    if len(cmt.matchedSequence) != 0:
        if len(pulse.adjacentSequence) != 0 and len(pulse.adjacentSequence2) == 0:
            if abs(cmt.matchedSequenceTime[0]-pulse.adjacentSequenceTime[0]) < 1/pulse.frequence:
                cmtAndPulseSequence = np.hstack((cmt.matchedSequence[::-1],pulse.adjacentSequence))
                cmtAndPulseSequenceTime = np.hstack((cmt.matchedSequenceTime[::-1],pulse.adjacentSequenceTime))
                globalFrequenz = 1/(cmtAndPulseSequenceTime[-1] - cmtAndPulseSequenceTime[0])


def setEmptyPlot(title = None,pen = "white"):
    global p
    p = win.addPlot(title=title)

def setPlot1(title = None,pen = "white"):
    global p1, curve1
    p1 = win.addPlot(title=title)
    curve1 = p1.plot(pen = pen)

def updatePlot1():
    global curve1
    curve1.setData(x = cmtAndPulseSequenceTime , y = cmtAndPulseSequence)

currentWithCmt = Signal(fullSequencePath="V2B_Current_Segment1.csv", querySequencePath="V2BCurrent_CMT.csv", downsample=2, threshold= 10000)
CurrentWithPuls = Signal(fullSequencePath="V2B_Current_Segment1.csv", querySequencePath="V2BCurrent_Puls.csv", downsample=2, threshold= 5000)
voltageWithZuendfehler = Signal(fullSequencePath="V2B_Voltage_Segment1.csv", querySequencePath="V2BVoltage_Zuendfehler.csv", downsample=2, threshold= 400)
voltageWithSpritzer = Signal(fullSequencePath="V2B_Voltage_Segment1.csv", querySequencePath="V2BVoltage_Spritzer02.csv", downsample=2, threshold= 1500)


power = Power(currentWithCmt,voltageWithZuendfehler)


app = pg.mkQApp("Spring Dashboard")
win = pg.GraphicsLayoutWidget(show=True)
win.setWindowTitle("Spring basic Dashboard")
win.resize(1000,600)


currentWithCmt.setPlot1("Strom Datastream",pen=(217,83,25))
currentWithCmt.setPlot2("CMT")
CurrentWithPuls.setPlot2("Puls(Single)")
CurrentWithPuls.setPlot4("DTW distance")

win.nextRow()

setEmptyPlot()
CurrentWithPuls.setPlot3("Puls-Phase")
setPlot1("CMT+Pulse")

win.nextRow()

voltageWithZuendfehler.setPlot1("Spannung Datastream",pen=(0,114,189))

voltageWithSpritzer.setPlot2("Spritzer")
voltageWithSpritzer.setPlot4("DTW distance Spritzer")
voltageWithZuendfehler.setPlot2("Zündfehler")

win.nextRow()
power.setPlot1("Leistung Datastream",pen=(126,47,142))
power.setPlot3("Energie",pen=(126,47,142))
setEmptyPlot()

qGraphicsGridLayout = win.ci.layout
qGraphicsGridLayout.setColumnStretchFactor(0,2)



def updateData():
    global N
    currentWithCmt.updateData()
    CurrentWithPuls.updateData(getAdjacentSequence = True)
    voltageWithZuendfehler.updateData()
    voltageWithSpritzer.updateData(findSpritzermode = True)
    power.updateSequence(currentWithCmt,voltageWithZuendfehler)
    power.calculateEnergy()
    getCmtAndPluse(currentWithCmt,CurrentWithPuls)



    if N % 15 == 0:

        currentWithCmt.updatePlot1()
        currentWithCmt.updatePlot2()
        CurrentWithPuls.updatePlot2()
        CurrentWithPuls.updatePlot3()
        CurrentWithPuls.updatePlot4()
        updatePlot1()

        voltageWithZuendfehler.updatePlot1()
        voltageWithZuendfehler.updatePlot2()
        voltageWithSpritzer.updatePlot2()
        voltageWithSpritzer.updatePlot4()


        power.updatePlot1()
        power.updatePlot3()

    N+=1


N = 0
timer = pg.QtCore.QTimer()
timer.timeout.connect(updateData)
timer.start(1)

if __name__ == '__main__':
    pg.exec()