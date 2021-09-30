#  File: Consanguinity.gpr.py
register(GRAMPLET,
         id="Consanguinity",
         name=_("Consanguinity"),
         description = _("Gramplet showing pedigree collapse and spousal consanguinity."),
         version="1.0.0",
         gramps_target_version="5.1",
         status = STABLE,
         fname="consanguinity.py",
         height = 50,
         detached_width = 400,
         detached_height = 500,
         gramplet = 'ConsanguinityGramplet',
         gramplet_title=_("Consanguinity"),
         help_url="5.1_Addons#Addon_List",
         navtypes=['Person']
         )
