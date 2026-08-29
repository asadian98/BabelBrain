# This Python file uses the following encoding: utf-8
from multiprocessing import Process,Queue
import os
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QVBoxLayout
from PySide6.QtCore import QFile,Slot,QObject,Signal,QThread,Qt
from PySide6.QtUiTools import QUiLoader


import numpy as np


#import cv2 as cv
import os
import sys
import platform
import time
import yaml
from BabelViscoFDTD.H5pySimple import ReadFromH5py
from GUIComponents.ScrollBars import ScrollBars as WidgetScrollBars

from CalculateFieldProcess import CalculateFieldProcess

from _BabelBasePhasedArray import BabelBasePhaseArray
from ConvMatTransform import (
    ReadTrajectoryBrainsight,
    read_itk_affine_transform,
    itk_to_BSight,
)
from TranscranialModeling.BabelIntegrationREMOPD import DeviceFrameSteering

_IS_MAC = platform.system() == 'Darwin'
def resource_path():  # needed for bundling
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if not _IS_MAC:
        return os.path.split(Path(__file__))[0]

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_dir = Path(sys._MEIPASS) / 'Babel_REMOPD'
    else:
        bundle_dir = Path(__file__).parent

    return bundle_dir

def format_ras_mm(xyz):
    return '%0.3f, %0.3f, %0.3f' % (float(xyz[0]), float(xyz[1]), float(xyz[2]))

def parse_ras_mm(text):
    parts = text.replace(',', ' ').replace(';', ' ').split()
    if len(parts) != 3:
        raise ValueError('Enter three numbers: X, Y, Z in millimetres (NIfTI RAS).')
    return np.array([float(parts[0]), float(parts[1]), float(parts[2])], dtype=float)

def trajectory_matrix_ras(config):
    path = config.get('OrigMat4Trajectory') or config.get('Mat4Trajectory')
    if not path or not os.path.isfile(path):
        path = config.get('Mat4Trajectory')
    if not path or not os.path.isfile(path):
        raise ValueError('No trajectory file is available yet. Run Step 1 first.')
    traj_type = str(config.get('TrajectoryType', 'brainsight')).lower()
    if traj_type == 'slicer':
        return itk_to_BSight(read_itk_affine_transform(path))
    return ReadTrajectoryBrainsight(path)

def gui_steering_from_targets_mm(R, virtual_ras, actual_ras):
    '''Map actual vs virtual RAS onto GUI / simulation steering (mm).

    Project (actual − virtual) onto the Brainsight tool axes (R columns).
    X: GUI +X = tool +X. Y: GUI +Y = −tool +Y (DeviceFrameSteering).
    Z: GUI +Z is depth from the array (normal, + = deeper). Brainsight tool +Z
    points toward the transducer, so the along-normal term is −tool[2].
    Returned along_beam is that already-signed delta to add to skin→virtual.
    '''
    delta = np.asarray(actual_ras, dtype=float) - np.asarray(virtual_ras, dtype=float)
    tool = R[:3, :3].T @ delta
    gui_x, gui_y = tool[0], -tool[1]
    along_beam = -float(tool[2])
    domain_x, domain_y = DeviceFrameSteering(gui_x, gui_y)
    return gui_x, gui_y, along_beam, float(domain_x), float(domain_y)

class REMOPD(BabelBasePhaseArray): 
    def __init__(self,parent=None,MainApp=None):
        super().__init__(parent=parent,MainApp=MainApp,formtype=os.path.join(resource_path(), "."))

    def load_ui(self,formtype):
        from Babel_REMOPD.REMOPDForm import REMOPDForm
        self.Widget = REMOPDForm(self)

        _l = QVBoxLayout(self)
        _l.setContentsMargins(0, 0, 0, 0)
        _l.addWidget(self.Widget)

        self.Widget.IsppaScrollBars = WidgetScrollBars(parent=self.Widget.IsppaScrollBars,MainApp=self)

        self.Widget.XSteeringSpinBox.setMinimum(self.Config['MinimalXSteering']*1e3)
        self.Widget.XSteeringSpinBox.setMaximum(self.Config['MaximalXSteering']*1e3)
        self.Widget.YSteeringSpinBox.setMinimum(self.Config['MinimalYSteering']*1e3)
        self.Widget.YSteeringSpinBox.setMaximum(self.Config['MaximalYSteering']*1e3)
        self.Widget.ZSteeringSpinBox.setMinimum(self.Config['MinimalZSteering']*1e3)
        self.Widget.ZSteeringSpinBox.setMaximum(self.Config['MaximalZSteering']*1e3)
        self.Widget.ZSteeringSpinBox.setValue(self.Config['DefaultZSteering']*1e3)
        
        self.Widget.SkinDistanceSpinBox.setMaximum(self.Config['MaxDistanceToSkin'])
        self.Widget.SkinDistanceSpinBox.setMinimum(-self.Config['MaxNegativeDistance'])  
        self.Widget.SkinDistanceSpinBox.setValue(0.0)

        self.Widget.RefocusingcheckBox.stateChanged.connect(self.EnableRefocusing)
        self.Widget.CalculateAcField.clicked.connect(self.RunSimulation)
        self.Widget.SkinDistanceSpinBox.valueChanged.connect(self.UpdateDistanceFromSkin)
        self.Widget.LabelTissueRemoved.setVisible(False)
        self.Widget.CalculateMechAdj.clicked.connect(self.CalculateMechAdj)
        self.Widget.CalculateMechAdj.setEnabled(False)
        # Virtual/actual RAS → X/Y/Z spinboxes; editing actual RAS refreshes the × marks.
        self.Widget.CalcSteerFromTargetsButton.clicked.connect(self.FillSteeringFromTargets)
        self.Widget.ActualTargetLineEdit.editingFinished.connect(self.OnActualTargetEdited)
        self.FillVirtualTargetFromTrajectory()
        self.up_load_ui()

    def GetExtraSuffixAcFields(self):
        # Must match BabelIntegrationREMOPD so Brainsight loads the steered NIfTI,
        # not an old unsuffixed file from a previous X/Y/Z/rot.
        return "_Steer_X_%2.1f_Y_%2.1f_Z_%2.1f_Rot_%2.1f_" % (
            self.Widget.XSteeringSpinBox.value(),
            self.Widget.YSteeringSpinBox.value(),
            self.Widget.ZSteeringSpinBox.value(),
            self.Widget.ZRotationSpinBox.value())

    def FillVirtualTargetFromTrajectory(self):
        # Origin of the Brainsight/Slicer 4×4 (the planning / virtual target).
        try:
            R = trajectory_matrix_ras(self._MainApp.Config)
        except (ValueError, OSError, KeyError):
            return
        self.Widget.VirtualTargetLineEdit.setText(format_ras_mm(R[:3, 3]))

    @Slot()
    def FillSteeringFromTargets(self):
        try:
            R = trajectory_matrix_ras(self._MainApp.Config)
            virtual = parse_ras_mm(self.Widget.VirtualTargetLineEdit.text())
            actual = parse_ras_mm(self.Widget.ActualTargetLineEdit.text())
        except ValueError as e:
            QMessageBox.warning(self, 'Targets', str(e))
            return
        gui_x, gui_y, along_beam, domain_x, domain_y = gui_steering_from_targets_mm(
            R, virtual, actual)
        # Z spinbox = axial depth from the array, not the RAS offset alone.
        z_virtual = self.Widget.DistanceSkinLabel.property('UserData')
        if z_virtual is None:
            z_virtual = self.Widget.ZSteeringSpinBox.value()
        gui_z = float(z_virtual) + along_beam
        xmin = self.Config['MinimalXSteering'] * 1e3
        xmax = self.Config['MaximalXSteering'] * 1e3
        ymin = self.Config['MinimalYSteering'] * 1e3
        ymax = self.Config['MaximalYSteering'] * 1e3
        zmin = self.Config['MinimalZSteering'] * 1e3
        zmax = self.Config['MaximalZSteering'] * 1e3
        in_range = (
            (xmin <= gui_x <= xmax) and (ymin <= gui_y <= ymax) and
            (zmin <= gui_z <= zmax)
        )
        msg = (
            'Offset from virtual (mm): lateral X %+0.1f, Y %+0.1f, along-normal %+0.1f.\n'
            'Steering (mm): X %+0.1f, Y %+0.1f, Z %+0.1f  (Z = virtual depth %+0.1f + along-normal).'
            % (domain_x, domain_y, along_beam, gui_x, gui_y, gui_z, float(z_virtual))
        )
        if not in_range:
            msg += (
                '\nOutside REMOPD range (X %+0.0f…%+0.0f, Y %+0.0f…%+0.0f, Z %.0f…%.0f mm).'
                % (xmin, xmax, ymin, ymax, zmin, zmax)
            )
        self.Widget.SteerFromTargetsLabel.setText(msg)
        if not in_range:
            ret = QMessageBox.question(
                self, 'Steering range',
                msg + '\n\nApply the values to the X/Y/Z spinboxes anyway?',
                QMessageBox.Yes | QMessageBox.No)
            if ret != QMessageBox.Yes:
                return
        self.Widget.XSteeringSpinBox.setValue(np.round(gui_x, 1))
        self.Widget.YSteeringSpinBox.setValue(np.round(gui_y, 1))
        self.Widget.ZSteeringSpinBox.setValue(np.round(gui_z, 1))
        self._MainApp.UpdateActualTargetMarks()
        
    @Slot()
    def UpdateDistanceFromSkin(self):
        self._bIgnoreUpdate=True
        CurDistance=self.Widget.SkinDistanceSpinBox.value()
        if CurDistance<0:
            self.Widget.LabelTissueRemoved.setVisible(True)
        else:
            self.Widget.LabelTissueRemoved.setVisible(False)

    def DefaultConfig(self):
        #Specific parameters for the REMOPD - to be configured later via a yaml

        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),'default.yaml'), 'r') as file:
            config = yaml.safe_load(file)
        print("REMOPD configuration:")
        print(config)

        self.Config=config

    def NotifyGeneratedMask(self):
        VoxelSize=self._MainApp._MaskNib.header.get_zooms()[0]
        TargetLocation =np.array(np.where(self._MainApp._FinalMask==5.0)).flatten()
        LineOfSight=self._MainApp._FinalMask[TargetLocation[0],TargetLocation[1],:]
        StartSkin=np.where(LineOfSight>0)[0].min()
        DistanceFromSkin = (TargetLocation[2]-StartSkin)*VoxelSize
        
        self.Widget.DistanceSkinLabel.setText('%3.2f'%(DistanceFromSkin))
        self.Widget.DistanceSkinLabel.setProperty('UserData',DistanceFromSkin)
        self.Widget.ZSteeringSpinBox.setValue(np.round(DistanceFromSkin,1))
        self.FillVirtualTargetFromTrajectory()
        self._MainApp.UpdateActualTargetMarks()


    def GetActualTargetRAS(self):
        # Parsed actual RAS, or None if the box is empty / invalid (other Tx skip this).
        try:
            return parse_ras_mm(self.Widget.ActualTargetLineEdit.text())
        except ValueError:
            return None

    def GetActualTargetDomainMm(self):
        '''Step-2 plot mm of the actual target: domain X/Y and axial Z from the array.'''
        try:
            R = trajectory_matrix_ras(self._MainApp.Config)
            virtual = parse_ras_mm(self.Widget.VirtualTargetLineEdit.text())
            actual = parse_ras_mm(self.Widget.ActualTargetLineEdit.text())
        except (ValueError, OSError, KeyError):
            return None
        gui_x, gui_y, along_beam, domain_x, domain_y = gui_steering_from_targets_mm(
            R, virtual, actual)
        z_virtual = self.Widget.DistanceSkinLabel.property('UserData')
        if z_virtual is None:
            z_virtual = getattr(self, '_DistanceToTarget', None)
        if z_virtual is None:
            z_virtual = self.Widget.ZSteeringSpinBox.value()
        return float(domain_x), float(domain_y), float(z_virtual) + along_beam

    def GetIntendedFocusPlotMm(self):
        # Mechanical adj. / FLHM distance must compare the focus cloud to the
        # actual × (aberration leftover), not the virtual + we steered away from.
        return self.GetActualTargetDomainMm()

    @Slot()
    def OnActualTargetEdited(self):
        self._MainApp.UpdateActualTargetMarks()


    @Slot()
    def RunSimulation(self):
        #we create an object to do a dryrun to recover filenames
        dry=RunAcousticSim(self._MainApp,bDryRun=True)
        FILENAMES = dry.run()
        
        self._FullSolName=FILENAMES['FilesSkull']
        self._WaterSolName=FILENAMES['FilesWater']

        bCalcFields=False
        bPrexistingFiles=True
        for sskull,swater in zip(self._FullSolName,self._WaterSolName):
            if not(os.path.isfile(sskull) and os.path.isfile(swater)):
                bPrexistingFiles=False
                break
            
        if bPrexistingFiles:
            #we can use the first entry, this is valid for all files in the list
            Skull=ReadFromH5py(self._FullSolName[0])
            XSteering=Skull['XSteering']
            YSteering=Skull['YSteering']
            ZSteering=Skull['ZSteering']
            if 'RotationZ' in Skull:
                RotationZ=Skull['RotationZ']
            else:
                RotationZ=0.0
                
            DistanceSkin =  -Skull['TxMechanicalAdjustmentZ']*1e3

            ret = QMessageBox.question(self,'', "Acoustic sim files already exist with:.\n"+
                                    "XSteering=%3.2f\n" %(XSteering*1e3)+
                                    "YSteering=%3.2f\n" %(YSteering*1e3)+
                                    "ZSteering=%3.2f\n" %(ZSteering*1e3)+
                                    "ZRotation=%3.2f\n" %(RotationZ)+
                                    "TxMechanicalAdjustmentX=%3.2f\n" %(Skull['TxMechanicalAdjustmentX']*1e3)+
                                    "TxMechanicalAdjustmentY=%3.2f\n" %(Skull['TxMechanicalAdjustmentY']*1e3)+
                                    "DistanceSkin=%3.2f\n" %(DistanceSkin)+
                                    "Do you want to recalculate?\nSelect No to reload",
                QMessageBox.Yes | QMessageBox.No)

            if ret == QMessageBox.Yes:
                bCalcFields=True
            else:
                self.Widget.XSteeringSpinBox.setValue(XSteering*1e3)
                self.Widget.YSteeringSpinBox.setValue(YSteering*1e3)
                self.Widget.ZSteeringSpinBox.setValue(ZSteering*1e3)
                self.Widget.ZRotationSpinBox.setValue(RotationZ)
                try:
                    self.Widget.RefocusingcheckBox.setChecked(Skull['bDoRefocusing'])
                except:
                    self.Widget.RefocusingcheckBox.setChecked(Skull['bDoRefocusing'].astype(int))
                self.Widget.MaxDepthSpinBox.setValue(Skull['zLengthBeyonFocalPoint']*1e3)
                TxSet = Skull['TxSet']
                if type(TxSet) is bytes:
                    TxSet=TxSet.decode("utf-8")
                index = self.Widget.SelTxSetDropDown.findText(TxSet, Qt.MatchFixedString)
                if index >= 0:
                    self.Widget.SelTxSetDropDown.setCurrentIndex(index)
                self.Widget.XMechanicSpinBox.setValue(Skull['TxMechanicalAdjustmentX']*1e3)
                self.Widget.YMechanicSpinBox.setValue(Skull['TxMechanicalAdjustmentY']*1e3)
                self.Widget.SkinDistanceSpinBox.setValue(DistanceSkin)
        else:
            bCalcFields = True
        self._bRecalculated = True
        if bCalcFields:
            self._MainApp.Widget.tabWidget.setEnabled(False)
            self.thread = QThread()
            self.worker = RunAcousticSim(self._MainApp)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.EndSimulation)
            self.worker.finished.connect(self._MainApp.SendTelemetry)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            self.worker.endError.connect(self.NotifyError)
            self.worker.endError.connect(self._MainApp.SendTelemetry)
            self.worker.endError.connect(self.thread.quit)
            self.worker.endError.connect(self.worker.deleteLater)

            self.worker.logTelemetry.connect(self._MainApp.LogTelemetry)

            self.thread.start()
            self._MainApp.showClockDialog()
        else:
            self.UpdateAcResults()

    def GetExport(self):
        Export=super(REMOPD,self).GetExport()
        Export['Refocusing']=self.Widget.RefocusingcheckBox.isChecked()
        def dict_to_string(d, separator=', ', equals_sign='='):
            return separator.join(f'{key}:{value*1000.0}' for key, value in d.items())
        # if self._MultiPoint is not None:
        #     st =''
        #     for e in self._MultiPoint:
        #         st+='[%s] ' % dict_to_string(e)
        #     Export['MultiPoint']=st
        # else:
        #     self._MultiPoint ='N/A'
         
        for k in ['XSteering','YSteering','ZSteering','ZRotation','XMechanic','YMechanic','SkinDistance']:
            Export[k]=getattr(self.Widget,k+'SpinBox').value()
        Export['VirtualTargetRAS']=self.Widget.VirtualTargetLineEdit.text()
        Export['ActualTargetRAS']=self.Widget.ActualTargetLineEdit.text()  # planning RAS, not a sim input
        return Export
    
    def EnableMultiPoint(self,MultiPoint):
        pass #we disable multipoint for the time being

class RunAcousticSim(QObject):

    finished = Signal(object)
    endError = Signal()
    logTelemetry = Signal(str)

    def __init__(self,mainApp,bDryRun=False):
        super(RunAcousticSim, self).__init__()
        self._mainApp=mainApp
        self._bDryRun=bDryRun

    def run(self):
        deviceName=self._mainApp.Config['ComputingDevice']
        COMPUTING_BACKEND=self._mainApp.Config['ComputingBackend']
        basedir,ID=os.path.split(os.path.split(self._mainApp.Config['T1WIso'])[0])
        basedir+=os.sep
        Target=[self._mainApp.Config['ID']+'_'+self._mainApp.Config['TxSystem']]

        InputSim=self._mainApp._outnameMask

        bRefocus = self._mainApp.AcSim.Widget.RefocusingcheckBox.isChecked()
        #we can use mechanical adjustments in other directions for final tuning
        if not bRefocus:
            TxMechanicalAdjustmentX= self._mainApp.AcSim.Widget.XMechanicSpinBox.value()/1e3 #in m
            TxMechanicalAdjustmentY= self._mainApp.AcSim.Widget.YMechanicSpinBox.value()/1e3  #in m
            TxMechanicalAdjustmentZ= -self._mainApp.AcSim.Widget.SkinDistanceSpinBox.value()/1e3  #in m

        else:
            TxMechanicalAdjustmentX=0
            TxMechanicalAdjustmentY=0
            TxMechanicalAdjustmentZ=0
        ###############
        XSteering=self._mainApp.AcSim.Widget.XSteeringSpinBox.value()/1e3 
        YSteering=self._mainApp.AcSim.Widget.YSteeringSpinBox.value()/1e3  
        ZSteering=self._mainApp.AcSim.Widget.ZSteeringSpinBox.value()/1e3  
        ##############
        RotationZ=self._mainApp.AcSim.Widget.ZRotationSpinBox.value()
        TxSet = self._mainApp.AcSim.Widget.SelTxSetDropDown.currentText()

        Frequencies = [self._mainApp._Frequency]

        basePPW=[self._mainApp._BasePPW]
        ZIntoSkin =0.0
        if TxMechanicalAdjustmentZ > 0:
            ZIntoSkin = np.abs(TxMechanicalAdjustmentZ)
        T0=time.time()

        kargs={}
        kargs['ID']=ID
        kargs['deviceName']=deviceName
        kargs['COMPUTING_BACKEND']=COMPUTING_BACKEND
        kargs['basePPW']=basePPW
        kargs['basedir']=basedir
        kargs['TxMechanicalAdjustmentZ']=TxMechanicalAdjustmentZ
        kargs['TxMechanicalAdjustmentX']=TxMechanicalAdjustmentX
        kargs['TxMechanicalAdjustmentY']=TxMechanicalAdjustmentY
        kargs['XSteering']=XSteering
        kargs['YSteering']=YSteering
        kargs['ZSteering']=ZSteering
        kargs['RotationZ']=RotationZ
        kargs['RotationZ']=RotationZ
        kargs['TxSet']=TxSet
        kargs['Frequencies']=Frequencies
        kargs['zLengthBeyonFocalPointWhenNarrow']=self._mainApp.AcSim.Widget.MaxDepthSpinBox.value()/1e3
        kargs['bDoRefocusing']=bRefocus
        kargs['bDryRun'] = self._bDryRun
        kargs['ZIntoSkin'] = ZIntoSkin
        kargs|=self._mainApp.CommomAcOptions()

        
        queue=Queue()
        if self._bDryRun == False:
            #in real run, we run this in background
            # Start mask generation as separate process.
            fieldWorkerProcess = Process(target=CalculateFieldProcess, 
                                        args=(queue,Target,self._mainApp.Config['TxSystem']),
                                        kwargs=kargs)
            fieldWorkerProcess.start()      
                
            # progress.
            T0=time.time()
            bNoError=True
            OutFiles=None
            while fieldWorkerProcess.is_alive():
                time.sleep(0.1)
                while queue.empty() == False:
                    cMsg=queue.get()
                    if type(cMsg) is str:
                        print(cMsg,end='')
                        if 'CTS:' in cMsg:
                            self.logTelemetry.emit(cMsg)
                        if '--Babel-Brain-Low-Error' in cMsg:
                            self.logTelemetry.emit("CTS:L1:S2: "+cMsg)
                            bNoError=False
                    else:
                        assert(type(cMsg) is dict)
                        OutFiles=cMsg
            fieldWorkerProcess.join()
            while queue.empty() == False:
                cMsg=queue.get()
                if type(cMsg) is str:
                    print(cMsg,end='')
                    if 'CTS:' in cMsg:
                        self.logTelemetry.emit(cMsg)
                    if '--Babel-Brain-Low-Error' in cMsg:
                        self.logTelemetry.emit("CTS:L1:S2: "+cMsg)
                        bNoError=False
                else:
                    assert(type(cMsg) is dict)
                    OutFiles=cMsg
            if bNoError:
                TEnd=time.time()
                TotalTime = TEnd-T0
                print('Total time',TotalTime)
                print("*"*40)
                print("*"*5+" DONE ultrasound simulation.")
                print("*"*40)
                self.logTelemetry.emit("CTS:L2:S2: TOTAL TIME " + str(TotalTime))
                self._mainApp.UpdateComputationalTime('ultrasound',TotalTime)
                self.finished.emit(OutFiles)
            else:
                print("*"*40)
                print("*"*5+" Error in execution.")
                print("*"*40)
                self.endError.emit()
        else:
            #in dry run, we just recover the filenames
            return CalculateFieldProcess(queue,Target,self._mainApp.Config['TxSystem'],**kargs)


if __name__ == "__main__":
    app = QApplication([])
    widget = REMOPD()
    widget.show()
    sys.exit(app.exec_())
