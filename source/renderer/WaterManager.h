/* Copyright (C) 2009 Wildfire Games.
 * This file is part of 0 A.D.
 *
 * 0 A.D. is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * 0 A.D. is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with 0 A.D.  If not, see <http://www.gnu.org/licenses/>.
 */

/*
 * Water settings (speed, height) and texture management
 */

#ifndef INCLUDED_WATERMANAGER
#define INCLUDED_WATERMANAGER

#include "graphics/Texture.h"
#include "ps/Overlay.h"
#include "maths/Matrix3D.h"
#include "lib/ogl.h"
#include "VertexBufferManager.h"


struct SWavesVertex {
	// vertex position
	CVector3D m_Position;
	u8 m_UV[2];
};
cassert(sizeof(SWavesVertex) == 16);



/**
 * Class WaterManager: Maintain water settings and textures.
 *
 * This could be extended to provide more advanced water rendering effects
 * (refractive/reflective water) in the future.
 */

class WaterManager
{
public:
	CTexturePtr m_WaterTexture[60];
	CTexturePtr m_NormalMap[60];
	CTexturePtr m_Foam;
	CTexturePtr m_Wave;
	u32* m_Heightmap;
	
	GLuint m_HeightmapTexture;
	GLuint m_OtherInfoTex;
	ssize_t m_TexSize;

	GLuint m_depthTT;
	GLuint m_waveTT;

	
	int m_WaterCurrentTex;
	CColor m_WaterColor;
	bool m_RenderWater;
	bool m_RunningSuperFancy;
	bool m_NeedsReloading;
	bool m_WaterScroll;
	float m_WaterHeight;
	float m_WaterMaxAlpha;
	float m_WaterFullDepth;
	float m_WaterAlphaOffset;

	float m_SWaterSpeed;
	float m_TWaterSpeed;
	float m_SWaterTrans;
	float m_TWaterTrans;
	float m_SWaterScrollCounter;
	float m_TWaterScrollCounter;
	double m_WaterTexTimer;

	// Reflection and refraction textures for fancy water
	GLuint m_ReflectionTexture;
	GLuint m_RefractionTexture;
	size_t m_ReflectionTextureSize;
	size_t m_RefractionTextureSize;

	// Model-view-projection matrices for reflected & refracted cameras
	// (used to let the vertex shader do projective texturing)
	CMatrix3D m_ReflectionMatrix;
	CMatrix3D m_RefractionMatrix;

	// Shader parameters for fancy water
	CColor m_WaterTint;
	float m_RepeatPeriod;
	float m_Shininess;
	float m_SpecularStrength;
	float m_Waviness;
	float m_Murkiness;
	CColor m_ReflectionTint;
	float m_ReflectionTintStrength;
	
	// Waves
	// see the struct above.
	CVertexBuffer::VBChunk* m_VBWaves;
	CVertexBuffer::VBChunk* m_VBWavesIndices;

public:
	WaterManager();
	~WaterManager();

	/**
	 * LoadWaterTextures: Load water textures from within the
	 * progressive load framework.
	 *
	 * @return 0 if loading has completed, a value from 1 to 100 (in percent of completion)
	 * if more textures need to be loaded and a negative error value on failure.
	 */
	int LoadWaterTextures();
	
	/**
	 * UnloadWaterTextures: Free any loaded water textures and reset the internal state
	 * so that another call to LoadWaterTextures will begin progressive loading.
	 */
	void UnloadWaterTextures();

	/**
	 * CreateSuperfancyInfo: creates textures and wave vertices for superfancy water
	 */
	void CreateSuperfancyInfo();

	/**
	 * Returns true if fancy water shaders will be used (i.e. the hardware is capable
	 * and it hasn't been configured off)
	 */
	bool WillRenderFancyWater();
	
	/**
	 * Returns true if super fancy water shaders will be used (i.e. the hardware is capable
	 * and it hasn't been configured off)
	 */
	bool WillRenderSuperFancyWater();
};


#endif // INCLUDED_WATERMANAGER
