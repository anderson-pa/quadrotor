from collections import namedtuple
from ctypes import *

# define return structures for DLL function calls
six_names = 'fx fy fz mx my mz'
six_array = namedtuple('SixArray', six_names)
field_six_array = [(name, c_short) for name in six_names.split()]

force_names = 'fx fy fz mx my mz v1 v2'
force_array = namedtuple('ForceArray', force_names)
field_force_array = [(name, c_short) for name in force_names.split()]

# VectorAxes contains four booleans:
#   x, y, z indicate if the coresponding axes are used to compute the vector
#   is_force indicates the vector is a force (if True) or momentum (if False)
vector_axes = namedtuple('VectorAxes', 'x y z is_force')


class ForceArray(Structure):
    _fields_ = field_force_array


class ClockedForceArray(Structure):
    _fields_ = [('clk', c_ushort)] + field_force_array


# load the DLL and apply return types as appropriate
jr3 = cdll.LoadLibrary('./jr3/jr3.dll')
jr3.GetForceArray.restype = ForceArray
jr3.GetClockedForceArray.restype = ClockedForceArray


class Jr3:
    def __init__(self, device_index=1, channel=0):
        self._handle = jr3.GetHandle(device_index)
        self._channel = channel

        self.self_test()
        self.set_peak_address(0)

    def _read_word(self, offset, restype=None):
        """Read a word from the JR3 memory space.

        Default return type is unsigned short (0 - 65535).

        :param offset: memory location to read
        :param restype: optional result type to cast to
        :return: int
        """
        val = jr3.ReadWord(self._handle, self._channel, offset)
        if restype is not None:
            val = restype(val).value
        return val

    def _read_words(self, offset, length, restype=None) -> list:
        """Read contiguous words from the JR3 memory space.

        Default return type is unsigned shorts (0 - 65535). This does not
        simply iterate over the python method (self._read_word), it calls a C++
        function, which should be faster (untested).

        :param offset: memory location to start reading
        :param length: length of memory block to read
        :param restype: optional result type to cast to
        :return: list(int)
        """
        if restype is None:
            restype = c_ushort
        words_def = restype * length
        words = words_def()
        jr3.ReadWords(self._handle, self._channel, offset, length, words)
        return list(words)

    def _read_word_list(self, offsets, restype=None) -> list:
        """Read non-contiguous words from the JR3 memory space.

        Default return type is unsigned shorts (0 - 65535). This is just a
        convenience function that iterates over the python method
        (self._read_word).

        :param offsets: memory locations to read
        :param restype: optional result type to cast to
        :return: list(int)
        """
        return [self._read_word(offset, restype) for offset in offsets]

    def _write_word(self, offset, value):
        """Write a word to the JR3 memory space.

        :param offset: memory location to write to
        :param value: data to write
        """
        jr3.WriteWord(self._handle, self._channel, offset, value)

    def _write_command(self, cw0, cw1=None, cw2=None):
        """Write command words to the JR3.

        Write values to the command addresses of the JR3. Words are written in
        reverse order (2, 1, 0) since it seems cw0 actually initiates the
        command.

        The JR3 indicates that the command was successfully completed by
        writing 0 to cw0 address. This value is returned but not checked for
        completion.

        :param cw0: value to write to command word 0
        :param cw1: (optional) value to write to command word 1
        :param cw2: (optional) value to write to command word 2
        :return: int value read from the cw0 memmory address
        """
        if cw2 is not None:
            self._write_word(0xe6, cw2)
        if cw1 is not None:
            self._write_word(0xe5, cw1)
        self._write_word(0xe7, cw0)

        return self._read_word(0xe7)

    def _scale_counts(self, fa):
        """Scale raw count values by the full scale.

        According to the manual, the maximum count is 2**14 (16384), so divide
        raw counts by that and multiply by full scale value to get the
        measurement in engineering units.

        :param force_array: list of counts (fx, fy, fz, mx, my, mz, v1, v2)
        :return: list(scaled counts)
        """
        return force_array(*[f / 2 ** 14 * fs
                             for f, fs, in zip(fa, self.fs)])

    def self_test(self):
        """Perform a simple self test to confirm some basic operation.

        Raises SystemError if copyright text does not match expected value.
        """
        # test read
        if self.copyright != 'C o p y r i g h t   J R 3   1 9 9 3 ':
            raise SystemError(f'JR3 failed self test. Copyright string mismatch: {self.copyright}')

        # test write
        offset = self._read_word(0x88, c_short)
        new_offset = 0
        if offset == new_offset:
           new_offset = -5
        self._write_word(0x88, new_offset)
        read_new_offset = self._read_word(0x88, c_short)
        if not new_offset == read_new_offset:
            raise SystemError(f'JR3 failed self test. Writing {new_offset} '
                              f'to 0x88 and read back {read_new_offset}')
        self._write_word(0x88, offset)

    @property
    def copyright(self):
        """Get the copyright text.

        :return: copyright string
        """
        copyright = self._read_words(0x40, 18)
        return ''.join([c.to_bytes(2, 'big').decode('utf-8') for c in copyright])

    @property
    def serial_num(self):
        """Get the serial number for the attached sensor.

        :return: int
        """
        return self._read_word(0xf8)

    @property
    def shunts(self):
        """Get the shunt readings.

        :return: list(int)
        """
        return six_array(*self._read_words(0x60, 6, c_short))

    def get_fs_min(self):
        return six_array(*self._read_words(0x70, 6))

    def get_fs_max(self):
        return six_array(*self._read_words(0x78, 6))

    def get_fs_defaults(self):
        return six_array(*self._read_words(0x68, 6))

    @property
    def fs(self):
        return force_array(*self._read_words(0x80, 8))

    @property
    def load_envelope(self):
        return self._read_word(0x6f)

    @property
    def active_transform(self):
        return self._read_word(0x77)

    @property
    def offsets(self):
        """Get the sensor offsets used to decouple the data.

        This should not normally be needed since the force readings already
        incorporate this into the result.

        :return: list(int)
        """
        return six_array(*self._read_words(0x88, 6, c_short))

    @offsets.setter
    def offsets(self, offsets):
        # convert namedtuples to dicts
        try:
            offsets = offsets._asdict()
        except AttributeError:
            pass

        for i, field in enumerate(six_names.split()):
            try:
                self._write_word(0x88 + i, offsets[field])
            except KeyError:
                pass

    @property
    def active_offset(self):
        return self._read_word(0x8e)

    @active_offset.setter
    def active_offset(self, active_offset):
        command = 0x0600 + active_offset % 16
        self._write_command(command)

    def reset_offsets(self):
        """Update the offsets to zero out the readings.

        According to the manual, this command uses filter2 to calculate
        offset values.
        """
        self._write_command(0x0800)

    @property
    def vector_axes(self):
        bits = [bool(b) for b in format(self._read_word(0x8f), '08b')[::-1]]
        v1 = vector_axes(*bits[:3], bits[6])
        v2 = vector_axes(*bits[3:6], not bits[7])
        return v1, v2

    def set_peak_address(self, filter=None, *, address=None):
        """Set which filter or address to monitor for peaks.

        One of the parameters must be supplied. Use 0-6 to select the
        corresponding filter to monitor, or 7 for rates. Optionally provide a
        specific address usign the address parameter. If both filter and
        address are provided, address will be ignored.

        The JR3 monitors a block of 8 values starting at the given address.

        :param filter: which filter to monitor (use 7 for 'rates')
        :param address: (optional) alternative address to monitor
        """
        if filter is not None:
            address = 0x90 + 8 * (filter % 8)
        if address is not None:
            self._write_word(0x7f, address)

    def get_peak_address(self):
        """Get the start address of block the JR3 is monitoring for peaks.

        The JR3 monitors a block of 8 values starting at the given address.

        :return: int address
        """
        return self._read_word(0x7f)

    def get_peaks(self, scaled=True, reset=True):
        """Read the peak values from the JR3.

        Get the minima and maxima for the values being monitored since the
        last reset. If reset is True, these peak values will be cleared for
        the next read.

        :param scaled: if True, scale from counts to calibrated units
        :param reset: if True, clear the peak values after reading
        :return: ForceArray(minima), ForceArray(maxima)
        """
        command = 0x0b00 if reset else 0x0c00
        self._write_command(command)

        minima = force_array(*self._read_words(0xd0, 8, c_short))
        maxima = force_array(*self._read_words(0xd8, 8, c_short))

        if scaled:
            minima = self._scale_counts(minima)
            maxima = self._scale_counts(maxima)
        return minima, maxima

    def get_max_forces(self):
        return

    def read_forces(self, filter=0, scaled=True):
        """Read the forces from the JR3 sensor.

        :param filter: select the filter to use (default = 0)
        :param scaled: if True, scale from counts to calibrated units
        :return: ForceArray named tuple
        """
        if filter < 0 or filter > 6:
            raise ValueError('filter must be 0-6 inclusive.')
        fa = jr3.GetForceArray(self._handle, self._channel, filter)
        fa = [getattr(fa, f[0]) for f in fa._fields_]

        if scaled:
            fa = self._scale_counts(fa)

        return force_array(*fa)

    def read_clocked_forces(self, filter=1, scaled=True):
        """Read the counter clock and forces from the JR3 sensor.

        This calls a C++ function to read the counter and forces as quickly as
        possible to minimize any delay between reads.

        The default filter is 1 since there is no counter for filter 0.

        :param filter: select the filter to use (default = 1)
        :param scaled: if True, scale from counts to calibrated units
        :return: clk, ForceArray named tuple
        """
        if filter < 1 or filter > 6:
            raise ValueError('filter must be 1-6 inclusive.')
        cfa = jr3.GetClockedForceArray(self._handle, self._channel, filter)
        cfa = [getattr(cfa, f[0]) for f in cfa._fields_]
        clk, *cfa = cfa

        if scaled:
            cfa = self._scale_counts(cfa)

        return clk, force_array(*cfa)

    @property
    def counters(self):
        """Read all the counter clocks for all six filters.

        :return: list(int)
        """
        return [c_ushort(cnt).value for cnt in self._read_words(0xe8, 6)]
