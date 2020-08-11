
#include <windows.h>
#include <crtdbg.h>

#include "JR3PCIIoctls.h"
#pragma pack(1)
#include "jr3pci_ft.h"
#include "string"

#define DLLEXPORT extern "C" __declspec(dllexport)

typedef struct clocked_force_array
{
    unsigned short count;
    short fx;
    short fy;
    short fz;
    short mx;
    short my;
    short mz;
    short v1;
    short v2;
} clocked_force_array;


DLLEXPORT ULONG GetDllVersion()
{
	ULONG version = 2;
	return version;
}

DLLEXPORT ULONG GetSupportedChannels(HANDLE hJr3PciDevice)
{
	JR3PCI_SUPPORTED_CHANNELS_RESPONSE_PARAMS SupportedChannelsResponseParams;

	DWORD dwBytesReturned = 0;
	BOOL bSuccess = DeviceIoControl(
		hJr3PciDevice,					                    // handle to device
		IOCTL_JR3PCI_SUPPORTED_CHANNELS,	                // operation
		NULL,				                                // input data buffer
		0,                                                  // size of input data buffer
		&SupportedChannelsResponseParams,	                // output data buffer
		sizeof(JR3PCI_SUPPORTED_CHANNELS_RESPONSE_PARAMS),  // size of output data buffer
		&dwBytesReturned,					                // byte count
		NULL);								                // overlapped information

	_ASSERTE(bSuccess && (dwBytesReturned == sizeof(JR3PCI_SUPPORTED_CHANNELS_RESPONSE_PARAMS)));

	return SupportedChannelsResponseParams.ulSupportedChannels;
}

DLLEXPORT HANDLE GetHandle(int iDeviceIndex)
{
	char szDeviceName[30];
	sprintf(szDeviceName, "\\\\.\\JR3PCI%d", iDeviceIndex);
	HANDLE hJr3PciDevice = CreateFile(
		szDeviceName,					// file name
		GENERIC_READ | GENERIC_WRITE,   // access mode
		0,								// share mode
		NULL,							// SD
		OPEN_EXISTING,					// how to create
		0,								// file attributes
		NULL);							// handle to template file

	if (hJr3PciDevice == INVALID_HANDLE_VALUE)
	{
		printf("Failed to open a handle to device '%s'.\r\n", szDeviceName);
		//continue;
	}
	printf("Handle to device '%s' opened successfully.\r\n", szDeviceName);

	return hJr3PciDevice;
}

DLLEXPORT void WriteWord(HANDLE hJr3PciDevice, UCHAR ucChannel, ULONG ulOffset, USHORT usData)
{
	JR3PCI_WRITE_WORD_REQUEST_PARAMS WriteWordRequestParams;
	WriteWordRequestParams.ucChannel = ucChannel;
	WriteWordRequestParams.ulOffset = ulOffset;
	WriteWordRequestParams.usData = usData;

	JR3PCI_WRITE_WORD_RESPONSE_PARAMS WriteWordResponseParams;

	DWORD dwBytesReturned = 0;
	BOOL bSuccess = DeviceIoControl(
		hJr3PciDevice,					            // handle to device
		IOCTL_JR3PCI_WRITE_WORD,					// operation
		&WriteWordRequestParams,				    // input data buffer
		sizeof(JR3PCI_WRITE_WORD_REQUEST_PARAMS),   // size of input data buffer
		&WriteWordResponseParams,				    // output data buffer
		sizeof(JR3PCI_WRITE_WORD_RESPONSE_PARAMS),  // size of output data buffer
		&dwBytesReturned,						    // byte count
		NULL);									    // overlapped information

	_ASSERTE(bSuccess && (dwBytesReturned == sizeof(JR3PCI_WRITE_WORD_RESPONSE_PARAMS)));
	_ASSERTE(WriteWordResponseParams.iStatus == JR3PCI_STATUS_OK);
}

DLLEXPORT WORD ReadWord(HANDLE hJr3PciDevice, UCHAR ucChannel, ULONG ulOffset)
{
	JR3PCI_READ_WORD_REQUEST_PARAMS ReadWordRequestParams;
	ReadWordRequestParams.ucChannel = ucChannel;
	ReadWordRequestParams.ulOffset = ulOffset;

	JR3PCI_READ_WORD_RESPONSE_PARAMS ReadWordResponseParams;

	DWORD dwBytesReturned = 0;
	BOOL bSuccess = DeviceIoControl(
		hJr3PciDevice,					            // handle to device
		IOCTL_JR3PCI_READ_WORD,					    // operation
		&ReadWordRequestParams,				        // input data buffer
		sizeof(JR3PCI_READ_WORD_REQUEST_PARAMS),    // size of input data buffer
		&ReadWordResponseParams,				    // output data buffer
		sizeof(JR3PCI_READ_WORD_RESPONSE_PARAMS),   // size of output data buffer
		&dwBytesReturned,						    // byte count
		NULL);									    // overlapped information

	_ASSERTE(bSuccess && (dwBytesReturned == sizeof(JR3PCI_READ_WORD_RESPONSE_PARAMS)));
	_ASSERTE(ReadWordResponseParams.iStatus == JR3PCI_STATUS_OK);

	return ReadWordResponseParams.usData;
}

DLLEXPORT void ReadWords(HANDLE hJr3PciDevice, UCHAR ucChannel, ULONG ulOffset, ULONG ulLength, unsigned short words[])
{
    for (ULONG i = 0; i < ulLength; i++)
	{
		words[i] = ReadWord(hJr3PciDevice, ucChannel, ulOffset + i);
	}
}

DLLEXPORT force_array GetForceArray(HANDLE hJr3PciDevice, UCHAR ucChannel, UCHAR ucFilter)
{
    force_array fa;
    unsigned short * pfa = (unsigned short *)&fa;
    ReadWords(hJr3PciDevice, ucChannel, 0x90 + 8*ucFilter, 8, pfa);
    return fa;
}

DLLEXPORT clocked_force_array GetClockedForceArray(HANDLE hJr3PciDevice, UCHAR ucChannel, UCHAR ucFilter)
{
    clocked_force_array cfa;
    cfa.count = ReadWord(hJr3PciDevice, ucChannel, COUNT1 - 1 + ucFilter);
    unsigned short * pcfa = (unsigned short *)&cfa.fx;
    ReadWords(hJr3PciDevice, ucChannel, 0x90 + 8*ucFilter, 8, pcfa);
    return cfa;
}