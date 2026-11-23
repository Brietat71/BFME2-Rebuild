// A record whose fifth word is zeroed in place.
#pragma once
#ifndef BFME2_RVA004D9A35FIELDS_H
#define BFME2_RVA004D9A35FIELDS_H

struct Rva004D9A35Fields
{
	Rva004D9A35Fields *clear();

	unsigned char m_unk0x00[0x14];
	int m_unk0x14;
};

#endif
