// Portions derived from Command & Conquer Generals and Command & Conquer Generals Zero Hour, (c) Electronic Arts Inc., GPL-3.0-or-later; see LICENSE and NOTICE.
// AABCollisionStruct.h: the working state of WWMath's moving axis-aligned box sweep (Zero Hour's colmathaabox.cpp).
// Target facts (retail game.dat): CollisionMath::Collide(AABoxClass, Vector3, AABoxClass, CastResultStruct *) 0x00723CE0
// builds one of these in a 0x30-byte frame with the constructor expanded in place: the start-bad flag at +0, the
// longest allowed fraction at +4, the axis and side at +8/+0xC, the centre offset at +0x10 and the relative move at
// +0x1C, then the two box references at +0x28 and +0x2C.
#pragma once
#ifndef BFME2_AABCOLLISIONSTRUCT_H
#define BFME2_AABCOLLISIONSTRUCT_H

#include "WWMath/AABoxClass.h"
#include "WWMath/Vector3.h"

struct AABCollisionStruct
{
	AABCollisionStruct(const AABoxClass &box0, const Vector3 &move0, const AABoxClass &box1, const Vector3 &move1) :
		StartBad(true),
		MaxFrac(0.0f),
		AxisId(-1),
		Side(0),
		Box0(box0),
		Box1(box1)
	{
		Vector3::Subtract(box1.Center, box0.Center, &C);
		Vector3::Subtract(move1, move0, &M);
	}

	bool StartBad;			// Inital configuration is intersecting?
	float MaxFrac;			// Longest move allowed so far
	int AxisId;			// Last separating axis
	int Side;			// which side of the interval

	Vector3 C;			// Vector from the center0 to center1
	Vector3 M;			// Move vector relative to stationary box0

	const AABoxClass &Box0;
	const AABoxClass &Box1;

private:
	//not implemented
	AABCollisionStruct(const AABCollisionStruct &);
	AABCollisionStruct &operator=(const AABCollisionStruct &);
};

typedef char AABCollisionStructSize[(sizeof(AABCollisionStruct) == 0x30) ? 1 : -1];

#endif
