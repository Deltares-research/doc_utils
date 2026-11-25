"""Names of the picture files that ``ddocs get-tex-template`` copies into the ``pictures/`` directory.

``ddocs clean --templates`` removes only these files from ``pictures/``, so images you added yourself are never
deleted. The list mirrors ``MiKTeX/tex/latex/deltares/pictures`` in the Deltares ``LatexInstallation`` repository.
Pictures added upstream after this list was written are left in place, which is the safe direction to be wrong in.
"""

TEMPLATE_PICTURES_DIR = "pictures"

TEMPLATE_PICTURES: tuple[str, ...] = (
    "01_deltares_rapport_omslag.jpg",
    "Deltares_logo_D-blauw_RGB.pdf",
    "Deltares_pay-off_D-blauw_RGB.pdf",
    "Deltares_pay-off_D-blauw_RGB.svg",
    "Deltares_pay-off_Wit_RGB.pdf",
    "Deltares_pay-off_Wit_RGB.svg",
    "action_arrow.pdf",
    "action_arrow.svg",
    "cover_transparant_circle.pdf",
    "cover_transparant_circle.svg",
    "cover_transparent_circle_icons.pdf",
    "cover_transparent_circle_icons.svg",
    "deltagoot.png",
    "deltares_address.png",
    "deltares_logo.pdf",
    "deltares_logo.svg",
    "deltares_merk.pdf",
    "deltares_merk.svg",
    "deltares_merk_pantone.pdf",
    "deltares_merk_pantone.svg",
    "deltares_name.pdf",
    "deltares_name.svg",
    "deltares_namelogo.pdf",
    "deltares_namelogo.svg",
    "landschap.jpg",
    "margin_note.pdf",
    "margin_note.svg",
    "margin_remark.pdf",
    "margin_remark.svg",
    "margin_restriction.pdf",
    "margin_restriction.svg",
    "margin_tip_left.pdf",
    "margin_tip_left.svg",
    "margin_tip_right.pdf",
    "margin_tip_right.svg",
    "margin_warning.pdf",
    "margin_warning.svg",
    "report_cover.pdf",
    "report_cover.svg",
    "report_cover_draft.pdf",
    "report_cover_draft.svg",
    "tetra_kantoor.png",
    "trein.jpg",
    "warning.png",
)
