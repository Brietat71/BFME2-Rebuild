// FontCharsClass.h: one GDI font's rendered glyph cache for Render2DSentenceClass.
// SIZE 0x464, base RefCountClass.
//
// Target facts (retail RVAs; table addresses are VAs). The allocation at 0x000901BD
// pushes 0x464 before operator new; the constructor is 0x00157950 and the destructor
// 0x00157390, which restores the class's own table VA 0x007D3C60 and then
// RefCountClass's VA 0x007C650C. That table has two slots, Delete_This (0x0006CE57,
// the RefCountClass body) and the deleting destructor 0x00157AB0 (calls 0x00157390),
// so the class adds no virtual of its own. The other two tables the constructor
// stores (VA 0x007D3BE8 at +0x10, base table VA 0x007D3B98 during teardown) are
// the vector member's, not the class's.
//
// Layout (constructor stores, Create_GDI_Font 0x00154630, Initialize_GDI_Font
// 0x001551C0, Is_Font 0x00154840, Get_Char_Data 0x00158520, Free_Character_Arrays
// 0x00154890): +0x08 the fallback font used for characters this font lacks,
// +0x0C the font's name (Initialize_GDI_Font formats it), +0x10 the 0x18-byte vector
// of glyph pages, +0x28..+0x38 the pixel metrics, +0x3C the point size, +0x40 an int
// Is_Font compares with its fourth argument (the point-size grid: see GameFont's
// rasterScale), +0x44 the GDI face name, +0x48 the GDI font handle, +0x4C a 256-entry
// table of ASCII glyph pointers, +0x44C the Unicode glyph table (allocated on
// demand; indexed from FirstUnicodeChar), +0x450 a 0xC-byte ordered tree (glyph id ->
// glyph pointer, searched by 0x001559C0), +0x45C/+0x45E the Unicode bounds, +0x460 the
// bold flag. A glyph pointer of 0xFFFFFFFF marks "known missing".
//
// Names follow the retail ledger (map names for the out-of-line members).
// The glyph record's two spellings in the map (struct and class) disagree; this
// header uses struct. Its first three words are the glyph id, spacing and width
// (Blit_Char loops over the +2 word as the bitmap's columns and stores its pixels
// through the pointer at +8; Get_Char_Width returns the +4 word, Get_Char_Metric and
// Get_Char_Spacing start from the +2 word).
#pragma once
#ifndef BFME2_WW3D2_FONTCHARSCLASS_H
#define BFME2_WW3D2_FONTCHARSCLASS_H

#include <string.h>
#include "Common/StlMap.h"
#include "WWLib/RefCountClass.h"
#include "WWLib/wwstring.h"
#include "WWLib/vector.h"

// 0x001541E0 allocates PixelCapacity unsigned shorts and clears the last word.
// 0x001564C9 compares the next glyph's end offset against PixelCapacity.
class FontCharsBuffer
{
public:
	FontCharsBuffer(int capacity) : PixelCapacity(capacity), m_unk0x08(0)	// 0x001541E0
	{
		Pixels = new unsigned short[capacity];
		memset(Pixels, 0, capacity * sizeof(unsigned short));
	}

	unsigned short *Pixels;
	int PixelCapacity;

private:
	unsigned m_unk0x08;
};

typedef char FontCharsBufferSize[(sizeof(FontCharsBuffer) == 0xC) ? 1 : -1];

struct FontCharsClassCharDataStruct
{
	unsigned short Value;									// +0x00 the character the glyph draws
	short Columns;											// +0x02 bitmap columns (Blit_Char's inner loop bound)
	short Advance;											// +0x04 what Get_Char_Width returns
	unsigned char m_gap0x6[2];
	unsigned short *Pixels;									// +0x08 the 4-4-4-4 bitmap Blit_Char expands
};

class FontCharsClass : public RefCountClass
{
public:
	FontCharsClass();
	virtual ~FontCharsClass();								// slot 1: 0x00157390, deleting dtor 0x00157AB0

	void Initialize_GDI_Font(const char *name, float point_size, bool is_bold, int grid);
	bool Is_Font(const char *name, float point_size, bool is_bold, int grid);
	const char *Get_Name() const { return Name; }
	int Get_Char_Height() const { return CharHeight; }
	int Get_Extra_Overlap() const { return PixelOverlap; }
	int Get_Char_Width(unsigned short c);
	int Get_Char_Metric(unsigned short c);
	int Get_Char_Spacing(unsigned short c);
	void Blit_Char(unsigned short c, unsigned short *dest, int dest_stride, int x, int y);
	void Blit_Char_Thai(unsigned short c, unsigned short *dest, int dest_stride, int x, int y);
	const FontCharsClassCharDataStruct *loadCharacterData(unsigned short c);

	FontCharsClass *AlternateUnicodeFont;					// +0x08 (public: W3DFontLibrary::loadFontData stores it)

private:
	void Create_GDI_Font(const char *face);
	void Free_Character_Arrays();
	const FontCharsClassCharDataStruct *Get_Char_Data(unsigned short c);
	void ensureCharPage(unsigned short c);
	const FontCharsClassCharDataStruct *loadCharBitmap(unsigned short c);
	const FontCharsClassCharDataStruct *Store_Thai_GDI_Glyph(unsigned short c);
	void Update_Current_Buffer(int width);

	StringClass Name;										// +0x0C
	DynamicVectorClass<FontCharsBuffer *> Buffers;			// +0x10 glyph pages
	int CurrPixelOffset;									// +0x28
	int CharHeight;											// +0x2C
	int CharAscent;											// +0x30
	int CharOverhang;										// +0x34
	int PixelOverlap;										// +0x38
	float PointSize;										// +0x3C
	int Grid;												// +0x40
	StringClass GDIFontName;								// +0x44
	void *GDIFont;											// +0x48 HFONT
	FontCharsClassCharDataStruct *ASCIICharArray[256];		// +0x4C
	FontCharsClassCharDataStruct **UnicodeCharArray;		// +0x44C
	_STL::map<unsigned short, FontCharsClassCharDataStruct *> CharTree;	// +0x450
	unsigned short FirstUnicodeChar;						// +0x45C
	unsigned short LastUnicodeChar;							// +0x45E
	bool IsBold;											// +0x460
};
typedef char FontCharsClassSizeCheck[sizeof(FontCharsClass) == 0x464 ? 1 : -1];

#endif
