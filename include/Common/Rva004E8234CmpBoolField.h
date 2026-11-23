// Whether a word field of an owner not yet recovered is set; the pad stands in for the owner.
#pragma once
#ifndef BFME2_RVA004E8234CMPBOOLFIELD_H
#define BFME2_RVA004E8234CMPBOOLFIELD_H

class Rva004E8234CmpBoolField
{
public:
	bool get() const;

private:
	unsigned char m_unk0x000[0x284];
	int m_value;
};

#endif
