-- lives in basedir/mapconfig/map_startboxes.lua
local layout = {
	[0] = {
	boxes = {
			{
			
			},
		},
	startpoints = {
		[STARTPOINT-1-TL],
		[STARTPOINT-1-TR],
		[STARTPOINT-1-BL],
		[STARTPOINT-1-BR],
		},
	nameLong = "[STARTPOINT-1-NAME]",
	nameShort = "[STARTPOINT-1-SHORT]",
	},
	[1] = {
	nameLong = "[STARTPOINT-2-NAME]",
	nameShort = "[STARTPOINT-2-NAME]",
	startpoints = {
		[STARTPOINT-2-TL],
		[STARTPOINT-2-TR],
		[STARTPOINT-2-BL],
		[STARTPOINT-2-BR],
		},
	boxes = {
			{
		
			},
		},
	},
}

return layout, { 2 }
