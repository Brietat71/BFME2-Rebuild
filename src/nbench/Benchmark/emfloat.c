#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define MEM_ARRAY_SIZE 20

#define ERROR_MEMORY 1
#define ERROR_MEMARRAY_FULL 2
#define ERROR_MEMARRAY_NOTFOUND 3
#define ERROR_FILEOPEN 10
#define ERROR_FILEWRITE 12
#define ERROR_FILEREAD 11
#define ERROR_FILEPROBE 13
#define ERROR_FILESEEK 14

static long randw = 13L;
static long randx = 117L;
static void *mem_array[2][MEM_ARRAY_SIZE];
static int mem_array_ents;
extern long global_align;

// Generated from the ledger; map snapshot c591f7146f88c8a8248ebb8ae22f0c978c22aed463db64e05ef57ff0dfae99cc
// object=O006B89A0 name-evidence=L
// Extents and edges are hypotheses; byte verification alone does not establish original TU boundaries.
// FUNCTION: BFME2 0x006B8950 size=72 name=?randnum@@YAJJ@Z evidence=N:ledger tier=B hypothesis:mm1-neighbour-shared-data
long randnum(long val)
{
	long rand;

	if (val != 0L)
	{
		randw = 13L;
		randx = 117L;
	}
	rand = (254754L * randw + 529562L * randx) % 1000075L;
	randx = randw;
	randw = rand;
	return rand;
}

// FUNCTION: BFME2 0x006B89A0 size=59 name=?bfmeRandom@@YAHH@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
int bfmeRandom(int num)
{
	return (int)(randnum(0L) % (long)num);
}

// FUNCTION: BFME2 0x006B89E0 size=65 name=?abs_randwc@@YAKK@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
unsigned long abs_randwc(unsigned long num)
{
	long temp = randnum(0L) % (long)num;
	if (temp < 0)
		temp = -temp;
	return (unsigned long)temp;
}

// FUNCTION: BFME2 0x006B8A40 size=11 name=?InitMemArray@@YAXXZ evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
void InitMemArray(void)
{
	mem_array_ents = 0;
}

// FUNCTION: BFME2 0x006B8A50 size=45 name=?Rva008791B0Add@@YAHPAX0@Z evidence=?:placeholder tier=B hypothesis:mm1-libs-upstream-path
int Rva008791B0Add(void *true_address, void *aligned_address)
{
	if (mem_array_ents >= MEM_ARRAY_SIZE)
		return -1;
	mem_array[0][mem_array_ents] = true_address;
	mem_array[1][mem_array_ents] = aligned_address;
	mem_array_ents++;
	return 0;
}

// FUNCTION: BFME2 0x006B8A80 size=96 name=?Rva008791E0Remove@@YAHPAXPAPAX@Z evidence=?:placeholder tier=B hypothesis:mm1-libs-upstream-path
int Rva008791E0Remove(void *aligned_address, void **true_address)
{
	int i;

	for (i = 0; i < mem_array_ents; i++)
		if (mem_array[1][i] == aligned_address)
			break;
	if (i >= mem_array_ents)
		return -1;
	*true_address = mem_array[0][i];
	for (i++; i < mem_array_ents; i++)
	{
		mem_array[0][i - 1] = mem_array[0][i];
		mem_array[1][i - 1] = mem_array[1][i];
	}
	mem_array_ents--;
	return 0;
}

// FUNCTION: BFME2 0x006B8AE0 size=44 name=?probeFile@@YAXPBDPAH@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
void probeFile(const char *filename, int *errorcode)
{
	FILE *fp = fopen(filename, "w");
	if (fp == NULL)
		*errorcode = ERROR_FILEOPEN;
	else
		*errorcode = 0;
	fclose(fp);
}

// FUNCTION: BFME2 0x006B8B10 size=37 name=?Rva00879270FileProbeStatus@@YAPAXPBDPAH@Z evidence=?:placeholder tier=B hypothesis:mm1-libs-upstream-path
void *Rva00879270FileProbeStatus(const char *filename, int *errorcode)
{
	FILE *fp = fopen(filename, "w+");
	if (fp == NULL)
		*errorcode = ERROR_FILEPROBE;
	else
		*errorcode = 0;
	return fp;
}

// FUNCTION: BFME2 0x006B8B40 size=25 name=?Rva008792A0CloseFile@@YAXPAXPAPAX@Z evidence=?:placeholder tier=B hypothesis:mm1-libs-upstream-path
void Rva008792A0CloseFile(void *fp, int *errorcode)
{
	fclose((FILE *)fp);
	*errorcode = 0;
}

// FUNCTION: BFME2 0x006B8B60 size=90 name=?readfile@@YAXPAUFILE@@KKPAXPAH@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
void readfile(FILE *fp, unsigned long offset, unsigned short nbytes, void *buffer, int *errorcode)
{
	*errorcode = 0;
	if (fseek(fp, offset, SEEK_SET) == -1)
	{
		*errorcode = ERROR_FILESEEK;
		return;
	}
	if (fread(buffer, 1, nbytes, fp) != nbytes)
		*errorcode = ERROR_FILEREAD;
}

// FUNCTION: BFME2 0x006B8BC0 size=90 name=?writefile@@YAXPAUFILE@@KKPAXPAH@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
void writefile(FILE *fp, unsigned long offset, unsigned short nbytes, void *buffer, int *errorcode)
{
	*errorcode = 0;
	if (fseek(fp, offset, SEEK_SET) == -1)
	{
		*errorcode = ERROR_FILESEEK;
		return;
	}
	if (fwrite(buffer, 1, nbytes, fp) == nbytes)
		*errorcode = ERROR_FILEWRITE;
}

// FUNCTION: BFME2 0x006B8C20 size=8 name=?ErrorExit@@YAXXZ evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
void ErrorExit(void)
{
	exit(1);
}

// FUNCTION: BFME2 0x006B8C40 size=11 name=?Rva008793B0@@YAHH@Z evidence=?:placeholder tier=B hypothesis:mm1-libs-upstream-path
unsigned long Rva008793B0(unsigned long startticks)
{
	return clock() - startticks;
}

// FUNCTION: BFME2 0x006B8C50 size=15 name=?rva008793c0@@YAII@Z evidence=?:placeholder tier=B hypothesis:mm1-libs-upstream-path
unsigned long rva008793c0(unsigned long tickamount)
{
	return tickamount / CLOCKS_PER_SEC;
}

// FUNCTION: BFME2 0x006B8C60 size=25 name=?bfmeScale@@YANI@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
double bfmeScale(unsigned long tickamount)
{
	return (double)tickamount / (double)CLOCKS_PER_SEC;
}

// FUNCTION: BFME2 0x006B8C80 size=204 name=?AllocateMemory@@YAPAXKPAH@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
void *AllocateMemory(unsigned long nbytes, int *errorcode)
{
	void *returnval;
	unsigned long true_addr;

	returnval = malloc(nbytes + 2L * global_align);
	if (returnval == NULL)
		*errorcode = ERROR_MEMORY;
	else
		*errorcode = 0;
	if (global_align == 0)
	{
		if (mem_array_ents >= MEM_ARRAY_SIZE)
		{
			*errorcode = ERROR_MEMARRAY_FULL;
			return returnval;
		}
		mem_array[0][mem_array_ents] = returnval;
		mem_array[1][mem_array_ents] = returnval;
		mem_array_ents++;
		return returnval;
	}
	true_addr = (unsigned long)returnval;
	if (global_align == 1)
	{
		if (!(true_addr & 1))
			true_addr++;
	}
	else
	{
		while (true_addr % global_align)
			true_addr++;
		if (!(true_addr % (2L * global_align)))
			true_addr += global_align;
	}
	if (mem_array_ents >= MEM_ARRAY_SIZE)
	{
		*errorcode = ERROR_MEMARRAY_FULL;
		return (void *)true_addr;
	}
	mem_array[0][mem_array_ents] = returnval;
	mem_array[1][mem_array_ents] = (void *)true_addr;
	mem_array_ents++;
	return (void *)true_addr;
}

// FUNCTION: BFME2 0x006B8D50 size=58 name=?FreeMemory@@YAXPAXPAH@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
void FreeMemory(void *mempointer, int *errorcode)
{
	if (Rva008791E0Remove(mempointer, &mempointer))
	{
		*errorcode = ERROR_MEMARRAY_NOTFOUND;
		return;
	}
	free(mempointer);
	*errorcode = 0;
}

// FUNCTION: BFME2 0x006B8D90 size=23 name=?SetInternalFPFZero@@YAXPAUInternalFPF@@E@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B8DB0 size=23 name=?SetInternalFPFInfinity@@YAXPAUInternalFPF@@E@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B8DD0 size=31 name=?SetInternalFPFNaN@@YAXPAUInternalFPF@@@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B8DF0 size=35 name=?IsMantissaZero@@YAHPAG@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B8E20 size=34 name=?Add16Bits@@YAXPAG0GG@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B8E50 size=34 name=?Sub16Bits@@YAXPAG0GG@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B8E80 size=129 name=?ShiftMantLeft1@@YAXPAG0@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B8F10 size=187 name=?ShiftMantRight1@@YAXPAG0@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B8FD0 size=83 name=?StickyShiftRightMant@@YAXPAUInternalFPF@@H@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B9030 size=43 name=?normalize@@YAXPAUInternalFPF@@@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B9060 size=51 name=?denormalize@@YAXPAUInternalFPF@@H@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B90A0 size=81 name=?RoundInternalFPF@@YAXPAUInternalFPF@@@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B9100 size=131 name=?choose_nan@@YAXPAUInternalFPF@@00H@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B9190 size=840 name=?AddSubInternalFPF@@YAXEPAUInternalFPF@@00@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B9510 size=672 name=?MultiplyInternalFPF@@YAXPAUInternalFPF@@00@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B97F0 size=740 name=?DivideInternalFPF@@YAXPAUInternalFPF@@00@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B9B20 size=106 name=?Int32ToInternalFPF@@YAXJPAUInternalFPF@@@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B9B90 size=170 name=?SetupCPUEmFloatArrays@@YAXPAUInternalFPF@@00K@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
// FUNCTION: BFME2 0x006B9C40 size=220 name=?DoEmFloatIteration@@YAKPAUInternalFPF@@00KK@Z evidence=N:ledger tier=B hypothesis:mm1-libs-upstream-path
