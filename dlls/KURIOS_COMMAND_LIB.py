from ctypes import *


class Kurios:
    KuriosLib = None
    isLoad = False

    @staticmethod
    def list_devices():
        """ List all connected Kurios devices
        Returns:
           The Kurios device list, each deice item is serialNumber/description
        """
        size = 10240
        str1 = create_string_buffer(size)
        result = Kurios.KuriosLib.common_List(str1, size)
        devicesStr = str1.value.decode("utf-8", "ignore").rstrip('\x00').split(',')
        length = len(devicesStr)
        i = 0
        devices = []
        devInfo = ["", ""]
        while i < length:
            str2 = devicesStr[i]
            if i % 2 == 0:
                if str2 != '':
                    devInfo[0] = str2
                else:
                    i += 1
            else:
                devInfo[1] = str2
                devices.append(devInfo.copy())
            i += 1
        return devices

    @staticmethod
    def load_library(path):
        Kurios.KuriosLib = cdll.LoadLibrary(path)
        Kurios.isLoad = True

    def __init__(self):
        lib_path = "./KURIOS_COMMAND_LIB_Win64.dll"
        if not Kurios.isLoad:
            Kurios.load_library(lib_path)
        self.hdl = -1

    def open(self, serialNo, nBaud, timeout):
        """ Open Kurios device
        Args:
            serialNo: serial number of the device to be opened, use GetPorts function to get exist list first
            nBaud: bit per second of port
            timeout: set timeout value in (s)
        Returns:
            non-negative number: hdl number returned Successful; negative number: failed.
        """
        ret = -1
        if Kurios.isLoad:
            ret = Kurios.KuriosLib.common_Open(serialNo.encode('utf-8'), nBaud, timeout)
            if ret >= 0:
                self.hdl = ret
            else:
                self.hdl = -1
        return ret

    def is_open(self, serialNo):
        """ Check opened status of Kurios device
        Args:
            serialNo: serial number of the device to be checked
        Returns:
            0: device is not opened; 1: device is opened.
        """
        ret = -1
        if Kurios.isLoad:
            ret = Kurios.KuriosLib.common_IsOpen(serialNo.encode('utf-8'))
        return ret

    def GetHandle(self, serialNo):
        """ get handle of port
        Args:
            serialNo: serial number of the device to be checked.
        Returns: 
            -1:no handle  non-negtive number: handle.
        """
        ret = -1
        if Kurios.isLoad:
            ret = Kurios.KuriosLib.common_GetHandle(serialNo.encode('utf-8'))
        return ret

    def close(self):
        """ Close opened Kurios device
        Args:
        Returns: 
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            ret = Kurios.KuriosLib.common_Close(self.hdl)
        return ret

    def GetID(self, id):
        """ Get the product header and firmware version
        Args:
            id: the model number, hardware and firmware versions
        Returns: 
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            idStr = create_string_buffer(1024)
            ret = Kurios.KuriosLib.kurios_Get_ID(self.hdl, idStr)
            id.append(idStr.raw.decode("utf-8").rstrip('\x00'))
        return ret

    def GetSpecification(self, Max, Min):
        """ Get connected filter's wavelength range.
        Args:
            Max: max wavelength
            Min: min wavelength
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            Maximum = c_int(0)
            Minimum = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_Specification(self.hdl, byref(Maximum), byref(Minimum))
            Max[0] = Maximum.value
            Min[0] = Minimum.value
        return ret

    def GetOpticalHeadType(self, filterSpectrumRange, availableBandwidthMode):
        """ Get filter spectrum range and available bandwidth mode.
        Args:
            filterSpectrumRange: 0000 0001 = Visible
                                 0000 0010 = NIR
                                 0000 0100 = IR(future model)
            availableBandwidthMode: 0000 0001 = BLACK
                                    0000 0010 = WIDE
                                    0000 0100 = MEDIUM
                                    0000 1000 = NARROW
                                    0001 0000 = SUPER NARROW (future model)
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            SpectrumRange = create_string_buffer(1024)
            BandwidthMode = create_string_buffer(1024)
            ret = Kurios.KuriosLib.kurios_Get_OpticalHeadType(self.hdl, SpectrumRange, BandwidthMode)
            filterSpectrumRange.append(SpectrumRange.raw.decode("utf-8").rstrip('\x00'))
            availableBandwidthMode.append(BandwidthMode.raw.decode("utf-8").rstrip('\x00'))
        return ret

    def SetOutputMode(self, value):
        """ Set output mode.
        Args:
            value: 1 = manual (PC or front panel control)
                   2 = sequenced, internal clock triggered
                   3 = sequenced, external triggered
                   4 = analog signal controlled,  internal clock triggered
                   5 = analog signal controlled, external triggered
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            mode = c_int(value)
            ret = Kurios.KuriosLib.kurios_Set_OutputMode(self.hdl, mode)
        return ret

    def GetOutputMode(self, value):
        """ Get the current output mode.
        Args:
            value: 1 = manual (PC or front panel control)
                   2 = sequenced, internal clock triggered
                   3 = sequenced, external triggered
                   4 = analog signal controlled,  internal clock triggered
                   5 = analog signal controlled, external triggered
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_OutputMode(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def SetBandwidthMode(self, value):
        """ Set the minimum output voltage limit for X axis.
        Args:
            value: 1 = BLACK mode
                   2 = WIDE mode
                   4 = MEDIUM mode
                   8 = NARROW mode
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            mode = c_int(value)
            ret = Kurios.KuriosLib.kurios_Set_BandwidthMode(self.hdl, mode)
        return ret

    def GetBandwidthMode(self, value):
        """ Get the maximum output voltage limit for X axis.
        Args:
            value: 1 = BLACK mode
                   2 = WIDE mode
                   4 = MEDIUM mode
                   8 = NARROW mode
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_BandwidthMode(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def SetWavelength(self, value):
        """ Set wavelength.
        Args:
            value: wavelength within the available wavelength range
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            wavelength = c_int(value)
            ret = Kurios.KuriosLib.kurios_Set_Wavelength(self.hdl, wavelength)
        return ret

    def GetWavelength(self, value):
        """ Get wavelength.
        Args:
            value: wavelength within the available wavelength range
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_Wavelength(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def SetSequenceStepData(self, index, wavelength, interval, bandwidthMode):
        """ Set sequence step data.
        Args:
            index: index
            wavelength: wavelength within filter range
            interval: time interval
            bandwidthMode: bandwidth mode
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            Index_val = c_int(index)
            wavelength_val = c_int(wavelength)
            interval_val = c_int(interval)
            bandwidthMode_val = c_int(bandwidthMode)
            ret = Kurios.KuriosLib.kurios_Set_SequenceStepData(self.hdl, Index_val, wavelength_val, interval_val,
                                                          bandwidthMode_val)
        return ret

    def GetSequenceStepData(self, index, wavelength, interval, bandwidthMode):
        """ Get sequence step data.
        Args:
             index: index
             wavelength: wavelength within filter range
             interval: time interval
             bandwidthMode: bandwidth mode
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            ind = c_int(index)
            wavele = c_int(0)
            inter = c_int(0)
            bandM = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_SequenceStepData(self.hdl, ind, byref(wavele), byref(inter),
                                                               byref(bandM))
            wavelength[0] = wavele.value
            interval[0] = inter.value
            bandwidthMode[0] = bandM.value
        return ret

    def GetAllSequenceData(self, value):
        """ Get the entire sequence of wavelength and time interval.
        Args:
            value: the entire sequence of wavelength and time interval
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = create_string_buffer(1024)
            ret = Kurios.KuriosLib.kurios_Get_AllSequenceData(self.hdl, byref(val))
            value.append(val.raw.decode("utf-8").rstrip('\x00'))
        return ret

    def SetInsertSequenceStep(self, index, wavelength, interval, bandwidthMode):
        """ Inserts an entry into the current sequence.
        Args:
             index: index
             wavelength: wavelength within filter range
             interval: time interval
             bandwidthMode: bandwidth mode
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            index_val = c_int(index)
            wavelength_val = c_int(wavelength)
            interval_val = c_int(interval)
            bandwidthMode_val = c_int(bandwidthMode)
            ret = Kurios.KuriosLib.kurios_Set_InsertSequenceStep(self.hdl, index_val, wavelength_val, interval_val,
                                                                 bandwidthMode_val)
        return ret

    def SetDeleteSequenceStep(self, value):
        """ Deletes an entry from the current sequence.
        Args:
            value: index of sequence step, 0 to delete all sequence
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            index = c_int(value)
            ret = Kurios.KuriosLib.kurios_Set_DeleteSequenceStep(self.hdl, index)
        return ret

    def SetDefaultWavelengthForSequence(self, value):
        """ Set default wavelength for sequence.
        Args:
            value: wavelength within the available wavelength range
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            wavelength = c_int(value)
            ret = Kurios.KuriosLib.kurios_Set_DefaultWavelengthForSequence(self.hdl, wavelength)
        return ret

    def GetDefaultWavelengthForSequence(self, value):
        """ Get the current default wavelength for all elements in sequence.
        Args:
            value: current default wavelength for all elements in sequence
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_DefaultWavelengthForSequence(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def SetDefaultBandwidthForSequence(self, value):
        """ Set bandwidth mode for all elements in sequence.
        Args:
            value: 2 = WIDE mode
                   4 = MEDIUM mode
                   8 = NARROW mode
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            bandwidth_mode = c_int(value)
            ret = Kurios.KuriosLib.kurios_Set_DefaultBandwidthForSequence(self.hdl, bandwidth_mode)
        return ret

    def GetDefaultBandwidthForSequence(self, value):
        """ Get the current default Bandwidth Mode for all elements in sequence.
        Args:
            value: 2 = WIDE mode
                   4 = MEDIUM mode
                   8 = NARROW mode
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_DefaultBandwidthForSequence(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def SetDefaultTimeIntervalForSequence(self, value):
        """ Set default time interval for sequence.
        Args:
            value: internal trigger default time between 1ms and 60000ms
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            interval = c_int(value)
            ret = Kurios.KuriosLib.kurios_Set_DefaultTimeIntervalForSequence(self.hdl, interval)
        return ret

    def GetDefaultTimeIntervalForSequence(self, value):
        """ Get the current internal trigger default time.
        Args:
            value: current internal trigger default time
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_DefaultTimeIntervalForSequence(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def GetSequenceLength(self, value):
        """ Get the sequence length.
        Args:
            value: sequence length
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_SequenceLength(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def GetStatus(self, value):
        """ Get the current filter status.
        Args:
            value: 0 = initialization
                   1 = warm up
                   2 = ready
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_Status(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def GetTemperature(self, value):
        """ Get the current filter temperature.
        Args:
            value: current filter temperature
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_double(0)
            ret = Kurios.KuriosLib.kurios_Get_Temperature(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def SetTriggerOutSignalMode(self, value):
        """ Set trigger out signal mode.
        Args:
            value: 0 = normal
                   1 = flipped
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            mode = c_int(value)
            ret = Kurios.KuriosLib.kurios_Set_TriggerOutSignalMode(self.hdl, mode)
        return ret

    def GetTriggerOutSignalMode(self, value):
        """ Get trigger output mode setting.
        Args:
            value:  0 = normal
                    1 = flipped
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_TriggerOutSignalMode(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def SetForceTrigger(self):
        """ Enforce one step ahead in external triggered sequence mode (Firmware version 3.1 or above).
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            ret = Kurios.KuriosLib.kurios_Set_ForceTrigger(self.hdl)
        return ret

    def GetTriggerOutTimeMode(self, value):
        """ Get trigger out time mode.
        Args:
            value:  0 =  normal waveform
                    1 =  trigger out signal start from wavelength switching completed and end with time countdown to zero
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_TriggerOutTimeMode(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def SetTriggerOutTimeMode(self, value):
        """ Set trigger out time mode.
        Args:
            value:  0 =  normal waveform
                    1 =  trigger out signal start from wavelength switching completed and end with time countdown to zero
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(value)
            ret = Kurios.KuriosLib.kurios_Set_TriggerOutTimeMode(self.hdl, val)
        return ret

    def GetDarkMode(self, value):
        """ Get control dark mode of controller, only for K2 version Kurios
        Args:
            value:  0 =  close
                    1 =  open
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(0)
            ret = Kurios.KuriosLib.kurios_Get_DarkMode(self.hdl, byref(val))
            value[0] = val.value
        return ret

    def SetDarkMode(self, value):
        """ Set control dark mode of controller, only for K2 version Kurios
        Args:
            value:  0 =  close
                    1 =  open
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = c_int(value)
            ret = Kurios.KuriosLib.kurios_Set_DarkMode(self.hdl, val)
        return ret

    def GetFastSwitchingData(self, value):
        """ Get fast switching data, only for K1 version Kurios.
        Args:
            value:  the fast switching data
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = create_string_buffer(8192)
            ret = Kurios.KuriosLib.kurios_Get_FastSwitchingData(self.hdl, byref(val))
            value.append(val.raw.decode("utf-8").rstrip('\x00'))
        return ret

    def GetFastTriggerData(self, value):
        """ Get fast trigger data, only for K2 version Kurios.
        Args:
            value:  the fast trigger data
        Returns:
            0: Success; negative number: failed.
        """
        ret = -1
        if self.hdl >= 0:
            val = create_string_buffer(8192)
            ret = Kurios.KuriosLib.kurios_Get_FastTriggerData(self.hdl, byref(val))
            value.append(val.raw.decode("utf-8").rstrip('\x00'))
        return ret
