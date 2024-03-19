#srmg_1
#by: Sestze

Creates a random map for Beyond All Reason.

Installation Instructions:
	Place script and folders inside of the pymapconv.exe's folder, execute script.

	Seed can be changed near the bottom of the script itself.

	Gentype can be changed in the map properties, currently has prefab, voronoi, paths, grid, perlin, and provided.

	Outputs the map to maps/srmg_gentype_fliptype_seed/srmg_gentype_fliptype_seed.sd7

You can add your own texture families for generation:
	1) Create a folder with the family name in /textures/families
	2) Place 24 bit .bmp textures in that folder
	3) Create a texturelist.txt file with the format of
		texturename,sizex,sizey
			List from lowest height to highest height.
	4) (OPTIONAL) Create a mapinfo.txt file with the format of
		[VARNAME],var
			These will be modified in the mapinfo.lua before the map is fully packaged.

You can add your own heightmap families for prefab generation:
	1) Create a folder with the family name in /prefab_generation/prefabs/
	2) Place 24 bit .bmp heightmaps in that folder
		(R, G, B) of (128, 128, 128) leaves the height the same in the heightmap. Less subtracts from the mapheight, and more adds to the mapheight.
	3) Create a fablist.txt file with the format of
		fabname,sizex,sizey

You can add your own heightmap for provided generation:
	1) Add a 24 bit .bmp to the /provided_generation/ directory
	2) point the "provided_filename" variable in map_properties to the image.

Dependencies:
	pypng
	py7zr
	PIL