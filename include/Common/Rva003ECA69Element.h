// A float followed by a block of sixteen words, both cleared together.
#pragma once
#ifndef BFME2_RVA003ECA69ELEMENT_H
#define BFME2_RVA003ECA69ELEMENT_H

class Rva003ECA69Element
{
public:
	void clear();

private:
	float m_value;
	int m_block[16];
};

#endif
