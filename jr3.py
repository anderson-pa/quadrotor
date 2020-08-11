from collections import namedtuple
from ctypes import *

# define return structures for DLL function calls
six_names = 'fx fy fz mx my mz'
six_array = namedtuple('SixArray', six_names)
field_six_array = [(name, c_short) for name in six_names.split()]

force_names = 'fx fy fz mx my mz v1 v2'
force_array = namedtuple('ForceArray', force_names)
field_force_array = [(name, c_short) for name in force_names.split()]


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

    def self_test(self):
        """Perform a simple self test to confirm some basic operation.

        Raises SystemError if copyright text does not match expected value.
        """
        # test read
        if self.copyright != 'C o p y r i g h t   J R 3   1 9 9 3 ':
            raise SystemError(f'JR3 failed self test. Copyright string mismatch: {self.copyright}')

        # test write

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
    def offsets(self):
        """Get the sensor offsets used to decouple the data.

        This should not normally be needed since the force readings already
        incorporate this into the result.

        :return: list(int)
        """
        return six_array(*self._read_words(0x88, 6, c_short))

    @property
    def fs_min(self):
        return six_array(*self._read_words(0x70, 6))

    @property
    def fs_max(self):
        return six_array(*self._read_words(0x78, 6))

    @property
    def fs(self):
        return force_array(*self._read_words(0x80, 8))

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
            fa = [f / 2 ** 14 * fs for f, fs, in zip(fa, self.fs)]

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
            cfa = [f / 2 ** 14 * fs for f, fs, in zip(cfa, self.fs)]

        return clk, force_array(*cfa)

    @property
    def counters(self):
        """Read all the counter clocks for all six filters.

        :return: list(int)
        """
        return [c_ushort(cnt).value for cnt in self._read_words(0xe8, 6)]

#  shunts 		0x60, 6
#  def fs 		0x68, 6
#  load env # 	0x6f
#  min fs		0x70, 6
#  xForm#		0x77
#  max fs		0x78, 6
#  fs			0x80, 8
##  ofs			0x88, 6
#  ofs#			0x8e
#  vect axes	0x8f

#  rate			0xc8, 8
#  min			0xd0, 8
#  max			0xd8, 8
