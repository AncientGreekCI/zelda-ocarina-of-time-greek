#!/usr/bin/env python3
"""
patch_menu_textures.py

Renders and injects polytonic Ancient Greek textures for:
1. do_action_static (HUD A-button actions: Attack, Check, Open, Speak, Grab, Dive, etc.)
2. icon_item_nes_static (Pause menu headers: Equipment, Map, Quest Status, Select Item, dungeon names, save prompt)
3. item_name_static (All 112 inventory and equipment item name banners)
4. title_static (File Select menu: Select File, Options, Copy, Erase, Sound, etc.)
5. place_title_cards (Area entrance calligraphy cards: Kokiri Forest, Temple of Time, Hyrule Field, etc.)
"""

import os
import struct
from typing import Dict, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import ipl3checksum

FONT_PATH = "fonts/GentiumPlus-Regular.ttf"

# ==============================================================================
# 1. Texture Definitions & Translations
# ==============================================================================

DO_ACTION_MAP: Dict[str, str] = {
    "gAttackDoActionENGTex": "Πλῆξον",
    "gCheckDoActionENGTex": "Σκόπει",
    "gEnterDoActionENGTex": "Εἴσελθε",
    "gReturnDoActionENGTex": "Πίσω",
    "gOpenDoActionENGTex": "Ἄνοιξον",
    "gJumpDoActionENGTex": "Πήδησον",
    "gDecideDoActionENGTex": "Κρῖνε",
    "gDiveDoActionENGTex": "Κατάδυθι",
    "gFasterDoActionENGTex": "Θᾶσσον",
    "gThrowDoActionENGTex": "Ῥῖψον",
    "gUnusedNaviDoActionENGTex": "Ναβί",
    "gClimbDoActionENGTex": "Ἀνάβηθι",
    "gDropDoActionENGTex": "Ἄφες",
    "gDownDoActionENGTex": "Κάτω",
    "gSaveDoActionENGTex": "Σῶσε",
    "gSpeakDoActionENGTex": "Λάλησον",
    "gNextDoActionENGTex": "Ἑξῆς",
    "gGrabDoActionENGTex": "Λαβοῦ",
    "gStopDoActionENGTex": "Στῆθι",
    "gPutAwayDoActionENGTex": "Ἀπόθου",
    "gReelDoActionENGTex": "Ἕλκυσον",
    "gNum1DoActionENGTex": "1",
    "gNum2DoActionENGTex": "2",
    "gNum3DoActionENGTex": "3",
    "gNum4DoActionENGTex": "4",
    "gNum5DoActionENGTex": "5",
    "gNum6DoActionENGTex": "6",
    "gNum7DoActionENGTex": "7",
    "gNum8DoActionENGTex": "8",
}

ICON_ITEM_NES_MAP: Dict[str, str] = {
    "gPauseDekuTitleENGTex": "Δένδρος Δέκου",
    "gPauseDodongoTitleENGTex": "Σπήλαιον Δοδόνγων",
    "gPauseJabuTitleENGTex": "Κοιλία Ἰαβοῦ-Ἰαβοῦ",
    "gPauseForestTitleENGTex": "Ναὸς τῆς Ὕλης",
    "gPauseFireTitleENGTex": "Ναὸς τοῦ Πυρός",
    "gPauseWaterTitleENGTex": "Ναὸς τοῦ Ὕδατος",
    "gPauseSpiritTitleENGTex": "Ναὸς τοῦ Πνεύματος",
    "gPauseShadowTitleENGTex": "Ναὸς τῆς Σκιᾶς",
    "gPauseBotWTitleENGTex": "Πυθμὴν Φρέατος",
    "gPauseIceCavernTitleENGTex": "Κρυσταλλῶδες Σπήλαιον",
    "gPauseToEquipENGTex": "Ἐξοπλίσαι",
    "gPauseToDecideENGTex": "Κρῖναι",
    "gPauseToPlayMelodyENGTex": "ᾎσαι Μέλος",
    "gPauseToSelectItemENGTex": "Ἐκλογὴ Σκευῶν",
    "gPauseToMapENGTex": "Χάρτης",
    "gPauseToQuestStatusENGTex": "Ἀγών",
    "gPauseToEquipmentENGTex": "Ἐξοπλισμός",
    "gPauseSavePromptENGTex": "Βούλῃ σῶσαι;",
    "gPauseSaveConfirmationENGTex": "Ἔσωσται ἡ πρόοδος.",
    "gPauseYesENGTex": "Ναί",
    "gPauseNoENGTex": "Οὔ",
    "gPauseCurrentPositionENGTex": "Θέσις",
}

ITEM_NAME_MAP: Dict[str, str] = {
    "gDekuStickItemNameENGTex": "Ῥάβδος Δέκου",
    "gDekuNutItemNameENGTex": "Κάρυον Δέκου",
    "gBombItemNameENGTex": "Βόμβα",
    "gFairyBowItemNameENGTex": "Νυμφικὸν Τόξον",
    "gFireArrowItemNameENGTex": "Βέλος Πυρός",
    "gDinsFireItemNameENGTex": "Πῦρ τῆς Δίν",
    "gFairySlingshotItemNameENGTex": "Νυμφικὴ Σφενδόνη",
    "gFairyOcarinaItemNameENGTex": "Νυμφικὴ Πλαγίαυλος",
    "gOcarinaOfTimeItemNameENGTex": "Πλαγίαυλος τοῦ Χρόνου",
    "gBombchuItemNameENGTex": "Βομβόμυς",
    "gHookshotItemNameENGTex": "Ἄγκιστρον",
    "gLongshotItemNameENGTex": "Μακρὸν Ἄγκιστρον",
    "gIceArrowItemNameENGTex": "Βέλος Κρυστάλλου",
    "gFaroresWindItemNameENGTex": "Ἄνεμος τῆς Φαρώρης",
    "gBoomerangItemNameENGTex": "Παλίντονος Βολίς",
    "gLensItemNameENGTex": "Φακὸς τῆς Ἀληθείας",
    "gMagicBeansItemNameENGTex": "Μαγικοὶ Κύαμοι",
    "gMegatonHammerItemNameENGTex": "Ὑπερμεγέθης Σφῦρα",
    "gLightArrowItemNameENGTex": "Βέλος Φωτός",
    "gNayrusLoveItemNameENGTex": "Ἀγάπη τῆς Νάιρυ",
    "gEmptyBottleItemNameENGTex": "Κενὴ Λήκυθος",
    "gRedPotionItemNameENGTex": "Ἐρυθρὸν Φάρμακον",
    "gGreenPotionItemNameENGTex": "Χλωρὸν Φάρμακον",
    "gBluePotionItemNameENGTex": "Κυανοῦν Φάρμακον",
    "gBottledFairyItemNameENGTex": "Νύμφη ἐν Ληκύθῳ",
    "gFishItemNameENGTex": "Ἰχθύς",
    "gFullMilkItemNameENGTex": "Γάλα Λὸν Λόν",
    "gRutosLetterItemNameENGTex": "Ἐπιστολὴ τῆς Ῥούτω",
    "gBlueFireItemNameENGTex": "Κυανοῦν Πῦρ",
    "gBugItemNameENGTex": "Ζωΰφιον",
    "gBigPoeItemNameENGTex": "Μέγα Πόε",
    "gHalfMilkItemNameENGTex": "Ἡμιτελὲς Γάλα",
    "gPoeItemNameENGTex": "Φάσμα Πόε",
    "gWeirdEggItemNameENGTex": "Ἄτοπον Ὠόν",
    "gCuccoItemNameENGTex": "Κουκκώ",
    "gZeldasLetterItemNameENGTex": "Ἐπιστολὴ τῆς Ζέλδας",
    "gKeatonMaskItemNameENGTex": "Προσωπεῖον Κίτωνος",
    "gSkullMaskItemNameENGTex": "Προσωπεῖον Κρανίου",
    "gSpookyMaskItemNameENGTex": "Φοβερὸν Προσωπεῖον",
    "gBunnyHoodItemNameENGTex": "Λαγῷα Ὦτα",
    "gGoronMaskItemNameENGTex": "Γορώνιον Προσωπεῖον",
    "gZoraMaskItemNameENGTex": "Ζώρειον Προσωπεῖον",
    "gGerudoMaskItemNameENGTex": "Γερούδειον Προσωπεῖον",
    "gMaskofTruthItemNameENGTex": "Προσωπεῖον Ἀληθείας",
    "gSOLDOUTItemNameENGTex": "Ἐπράθη",
    "gPocketEggItemNameENGTex": "Ἐγκόλπιον Ὠόν",
    "gPocketCuccoItemNameENGTex": "Ἐγκόλπιος Κουκκώ",
    "gCojiroItemNameENGTex": "Κοτζίρο",
    "gOddMushroomItemNameENGTex": "Ἄτοπος Μύκης",
    "gOddPotionItemNameENGTex": "Ἄτοπον Φάρμακον",
    "gPoachersSawItemNameENGTex": "Πρίων τοῦ Λαθροθήρα",
    "gBrokenGoronsSwordItemNameENGTex": "Κατεαγὸς Γορώνιον Ξίφος",
    "gPrescriptionItemNameENGTex": "Συνταγή",
    "gEyeBallFrogItemNameENGTex": "Ὀφθαλμοβάτραχος",
    "gEyeDropsItemNameENGTex": "Κολλύριον",
    "gClaimCheckItemNameENGTex": "Σύμβολον Παραλαβῆς",
    "gKokiriSwordItemNameENGTex": "Κοκιρικὸν Ξίφος",
    "gMasterSwordItemNameENGTex": "Τὸ Κύριον Ξίφος",
    "gGiantsKnifeItemNameENGTex": "Μαχαίρα τοῦ Γίγαντος",
    "gDekuShieldItemNameENGTex": "Θυρεὸς Δέκου",
    "gHylianShieldItemNameENGTex": "Ὑλικὸς Θυρεός",
    "gMirrorShieldItemNameENGTex": "Κατοπτρικὸς Θυρεός",
    "gKokiriTunicItemNameENGTex": "Κοκιρικὸς Χιτών",
    "gGoronTunicItemNameENGTex": "Γορώνιος Χιτών",
    "gZoraTunicItemNameENGTex": "Ζώρειος Χιτών",
    "gKokiriBootsItemNameENGTex": "Κοκιρικὰ Ὑποδήματα",
    "gIronBootsItemNameENGTex": "Σιδηρᾶ Ὑποδήματα",
    "gHoverBootsItemNameENGTex": "Ἐπιπολάζοντα Ὑποδήματα",
    "gBulletBag30ItemNameENGTex": "Θύλακος (30)",
    "gBulletBag40ItemNameENGTex": "Θύλακος (40)",
    "gBulletBag50ItemNameENGTex": "Θύλακος (50)",
    "gQuiver30ItemNameENGTex": "Φαρέτρα (30)",
    "gQuiver40ItemNameENGTex": "Φαρέτρα (40)",
    "gQuiver50ItemNameENGTex": "Φαρέτρα (50)",
    "gBombBag20ItemNameENGTex": "Βομβοφόρος (20)",
    "gBombBag30ItemNameENGTex": "Βομβοφόρος (30)",
    "gBombBag40ItemNameENGTex": "Βομβοφόρος (40)",
    "gGoronsBraceletItemNameENGTex": "Ψέλιον τῶν Γορώνων",
    "gSilverGauntletsItemNameENGTex": "Ἀργυραῖ Χειρίδες",
    "gGoldenGauntletsItemNameENGTex": "Χρυσαῖ Χειρίδες",
    "gSilverScaleItemNameENGTex": "Ἀργυρᾶ Λεπίς",
    "gGoldenScaleItemNameENGTex": "Χρυσῆ Λεπίς",
    "gBrokenGiantsKnifeItemNameENGTex": "Κατεαγυῖα Μαχαίρα",
    "gMinuetOfForestItemNameENGTex": "Μινουέτον τῆς Ὕλης",
    "gBoleroOfFireItemNameENGTex": "Μπολερὸ τοῦ Πυρός",
    "gSerenadeOfWaterItemNameENGTex": "Σερενάτα τοῦ Ὕδατος",
    "gRequiemOfSpiritItemNameENGTex": "Ἐπιτάφιον Πνεύματος",
    "gNocturneOfShadowItemNameENGTex": "Νυκτερινὸν τῆς Σκιᾶς",
    "gPreludeOfLightItemNameENGTex": "Προοίμιον τοῦ Φωτός",
    "gZeldasLullabyItemNameENGTex": "Κατακοίμισμα Ζέλδας",
    "gEponasSongItemNameENGTex": "ᾠδὴ τῆς Ἐπώνας",
    "gSariasSongItemNameENGTex": "ᾠδὴ τῆς Σαρίας",
    "gSunsSongItemNameENGTex": "ᾠδὴ τοῦ Ἡλίου",
    "gSongOfTimeItemNameENGTex": "ᾠδὴ τοῦ Χρόνου",
    "gSongOfStormsItemNameENGTex": "ᾠδὴ Καταιγίδων",
    "gForestMedallionItemNameENGTex": "Μετάλλιον τῆς Ὕλης",
    "gFireMedallionItemNameENGTex": "Μετάλλιον τοῦ Πυρός",
    "gWaterMedallionItemNameENGTex": "Μετάλλιον τοῦ Ὕδατος",
    "gSpiritMedallionItemNameENGTex": "Μετάλλιον Πνεύματος",
    "gShadowMedallionItemNameENGTex": "Μετάλλιον τῆς Σκιᾶς",
    "gLightMedallionItemNameENGTex": "Μετάλλιον τοῦ Φωτός",
    "gKokiriEmeraldItemNameENGTex": "Σμάραγδος Κοκίρι",
    "gGoronsRubyItemNameENGTex": "Ῥουβίνιον Γορώνων",
    "gZorasSapphireItemNameENGTex": "Σάπφειρος Ζῶρα",
    "gStoneofAgonyItemNameENGTex": "Λίθος τῆς Ἀγωνίας",
    "gGerudosCardItemNameENGTex": "Γνώρισμα Γερούδων",
    "gGoldSkulltulaItemNameENGTex": "Χρυσῆ Σκουλτούλα",
    "gPieceOfHeartItemNameENGTex": "Τεμάχιον Καρδίας",
    "gUnusedBigKeyItemNameENGTex": "Μέγα Κλειδίον",
    "gCompassItemNameENGTex": "Πυξίς",
    "gDungeonMapItemNameENGTex": "Χάρτης Δεσμωτηρίου",
    "gBiggoronsSwordItemNameENGTex": "Ξίφος Μεγαλογόρωνος",
}

TITLE_STATIC_MAP: Dict[str, str] = {
    "gFileSelSOUNDENGTex": "Ἦχος",
    "gFileSelENDButtonENGTex": "Τέλος",
    "gFileSelNoFileToCopyENGTex": "Οὐδὲν ἀρχεῖον πρὸς ἀντιγραφήν",
    "gFileSelNoFileToEraseENGTex": "Οὐδὲν ἀρχεῖον πρὸς διαγραφήν",
    "gFileSelNoEmptyFileENGTex": "Οὐδὲν κενὸν ἀρχεῖον",
    "gFileSelFileEmptyENGTex": "Κενὸν Ἀρχεῖον",
    "gFileSelFileInUseENGTex": "Ἐν Χρήσει",
    "gFileSelCopyWhichFileENGTex": "Ποῖον ἀρχεῖον ἀντιγράψαι;",
    "gFileSelCopyToWhichFileENGTex": "Εἰς ποῖον ἀρχεῖον ἀντιγράψαι;",
    "gFileSelAreYouSureENGTex": "Βέβαιος εἶ;",
    "gFileSelFileCopiedENGTex": "Ἀντεγράφη τὸ ἀρχεῖον",
    "gFileSelPleaseSelectAFileENGTex": "Ἐπίλεξον ἀρχεῖον",
    "gFileSelOpenThisFileENGTex": "Ἄνοιξον τόδε τὸ ἀρχεῖον;",
    "gFileSelEraseWhichFileENGTex": "Ποῖον ἀρχεῖον διαγράψαι;",
    "gFileSelAreYouSure2ENGTex": "Ἆρα παντάπασι βέβαιος εἶ;",
    "gFileSelFileErasedENGTex": "Διεγράφη τὸ ἀρχεῖον",
    "gFileSelOptionsENGTex": "Ἐπιλογαί",
    "gFileSelNameENGTex": "Ὄνομα",
    "gFileSelSurroundENGTex": "Περιφερ.",
    "gFileSelHeadsetENGTex": "Ἀκουστικ.",
    "gFileSelMonoENGTex": "Μονοφων.",
    "gFileSelStereoENGTex": "Στερεοφ.",
    "gFileSelZTargetingENGTex": "[Z]-Σκόπευσις",
    "gFileSelSwitchENGTex": "Ἐναλλαγή",
    "gFileSelHoldENGTex": "Κράτησις",
    "gFileSelControlsENGTex": "Χειρισμός",
    "gFileSelCheckBrightnessENGTex": "Φωτεινότης",
    "gFileSelCopyButtonENGTex": "Ἀντίγραψον",
    "gFileSelFile1ButtonENGTex": "Ἀρχεῖον 1",
    "gFileSelFile2ButtonENGTex": "Ἀρχεῖον 2",
    "gFileSelFile3ButtonENGTex": "Ἀρχεῖον 3",
    "gFileSelYesButtonENGTex": "Ναί",
    "gFileSelEraseButtonENGTex": "Διάγραψον",
    "gFileSelOptionsButtonENGTex": "Ἐπιλογαί",
    "gFileSelQuitButtonENGTex": "Ἐξελθεῖν",
    "gFileSelSaveXENGTex": "Σῶσον",
}

PLACE_TITLE_MAP: Dict[str, str] = {
    "gForestTempleTitleCardENGTex": "Ναὸς τῆς Ὕλης",
    "gShadowTempleTitleCardENGTex": "Ναὸς τῆς Σκιᾶς",
    "gFireTempleTitleCardENGTex": "Ναὸς τοῦ Πυρός",
    "gWaterTempleTitleCardENGTex": "Ναὸς τοῦ Ὕδατος",
    "gSpiritTempleTitleCardENGTex": "Ναὸς τοῦ Πνεύματος",
    "gDekuTreeTitleCardENGTex": "Δένδρος Δέκου",
    "gJabuJabuTitleCardENGTex": "Κοιλία τοῦ Ἰαβοῦ-Ἰαβοῦ",
    "gDodongosCavernTitleCardENGTex": "Σπήλαιον τῶν Δοδόνγων",
    "gInsideGanonsCastleTitleCardENGTex": "Ἔνδον Φρουρίου Γάνωνος",
    "gIceCavernTitleCardENGTex": "Κρυσταλλῶδες Σπήλαιον",
    "gGERudoTrainingGroundTitleCardENGTex": "Γυμνάσιον Γερούδων",
    "gCastleCourtyardTitleCardENGTex": "Αὐλὴ τοῦ Φρουρίου",
    "gGreatFairysFountainTitleCardENGTex": "Πηγὴ Μεγάλης Νύμφης",
    "gChamberOfTheSagesTitleCardENGTex": "Βουλευτήριον τῶν Σοφῶν",
    "gShootingGalleryTitleCardENGTex": "Τοξικὸν Στάδιον",
    "gTempleOfTimeTitleCardENGTex": "Ναὸς τοῦ Χρόνου",
    "gMarketTitleCardENGTex": "Ἡ Ἀγορά",
    "gBackAlleyTitleCardENGTex": "Στενωπός",
    "gKokiriShopTitleCardENGTex": "Ἐργαστήριον Κοκίρι",
    "gGoronShopTitleCardENGTex": "Ἐργαστήριον Γορώνων",
    "gZoraShopTitleCardENGTex": "Ἐργαστήριον Ζῶρα",
    "gHouseOfSkulltulaTitleCardENGTex": "Οἰκία τῆς Σκουλτούλας",
    "gBazaarTitleCardENGTex": "Τὸ Παντοπωλεῖον",
    "gPotionShopTitleCardENGTex": "Φαρμακοπωλεῖον",
    "gGravekeepersHutTitleCardENGTex": "Καλύβη Ταφοφύλακος",
    "gLakesideLaboratoryTitleCardENGTex": "Παραλίμνιον Ἐργαστήριον",
    "gHyruleFieldTitleCardENGTex": "Πεδίον τῆς Ὑρούλης",
    "gKakarikoVillageTitleCardENGTex": "Κώμη Κακαρικό",
    "gGraveyardTitleCardENGTex": "Τὰ Μνήματα",
    "gZorasRiverTitleCardENGTex": "Ποταμὸς τῶν Ζῶρα",
    "gKokiriForestTitleCardENGTex": "Δρυμὸς τῶν Κοκίρι",
    "gLakeHyliaTitleCardENGTex": "Λίμνη Ὑλία",
    "gZorasDomainTitleCardENGTex": "Ἐπικράτεια τῶν Ζῶρα",
    "gZorasFountainTitleCardENGTex": "Πηγὴ τῶν Ζῶρα",
    "gGERudoValleyTitleCardENGTex": "Φάραγξ τῶν Γερούδων",
    "gLostWoodsTitleCardENGTex": "Δρυμὸς τῆς Πλάνης",
    "gHauntedWastelandTitleCardENGTex": "Ἔρημος τῶν Φαντασμάτων",
    "gHyruleCastleTitleCardENGTex": "Φρούριον τῆς Ὑρούλης",
    "gDeathMountainTrailTitleCardENGTex": "Ἀτραπὸς Ὄρους Θανάτου",
    "gDeathMountainCraterTitleCardENGTex": "Κρατὴρ Ὄρους Θανάτου",
    "gGoronCityTitleCardENGTex": "Πόλις τῶν Γορώνων",
    "gLonLonRanchTitleCardENGTex": "Ἔπαυλις Λὸν Λόν",
    "gGanonsCastleTitleCardENGTex": "Φρούριον τοῦ Γάνωνος",
    "gRoyalFamilysTombTitleCardENGTex": "Βασιλικὸς Τάφος",
    "gFairysFountainTitleCardENGTex": "Πηγὴ τῆς Νύμφης",
    "gFishingPondTitleCardENGTex": "Δεξαμενὴ Ἁλιείας",
    "gBombchuBowlingAlleyCardENGTex": "Στάδιον Βομβομύων",
    "gStableTitleCardENGTex": "Ἱπποστάσιον",
    "gThievesHideoutTitleCardENGTex": "Κρησφύγετον Λῃστῶν",
    "gHappyMaskShopTitleCardENGTex": "Ἐργαστήριον Προσωπείων",
    "gTreasureBoxShopTitleCardENGTex": "Ἐργαστήριον Κιβωτῶν",
    "gSacredForestMeadowTitleCardENGTex": "Ἱερὸς Λειμὼν Δρυμοῦ",
    "gGERudosFortressTitleCardENGTex": "Ὀχύρωμα τῶν Γερούδων",
    "gBottomOfTheWellTitleCardENGTex": "Πυθμὴν τοῦ Φρέατος",
    "gDesertColossusTitleCardENGTex": "Κολοσσὸς τῆς Ἐρήμου",
    "gBombchuShopTitleCardENGTex": "Βομβομυοπωλεῖον",
    "gQuestionMarkTitleCardENGTex": ";",
}

MAP_NAME_MAP: Dict[str, str] = {
    # 12 World Map Point Names (128x16 ia4)
    "gHauntedWastelandPointNameENGTex": "Ἔρημος Φαντασμάτων",
    "gGerudosFortressPointNameENGTex": "Ὀχύρωμα Γερούδων",
    "gGerudoValleyPointNameENGTex": "Φάραγξ Γερούδων",
    "gHyliaLakesidePointNameENGTex": "Ὄχθη τῆς Ὑλίας",
    "gLonLonRanchPointNameENGTex": "Ἔπαυλις Λὸν Λόν",
    "gMarketPointNameENGTex": "Ἀγορά",
    "gHyruleFieldPointNameENGTex": "Πεδίον Ὑρούλης",
    "gDeathMountainPointNameENGTex": "Ὄρος τοῦ Θανάτου",
    "gKakarikoVillagePointNameENGTex": "Κώμη Κακαρικό",
    "gLostWoodsPointNameENGTex": "Δρυμὸς τῆς Πλάνης",
    "gKokiriForestPointNameENGTex": "Δρυμὸς Κοκίρι",
    "gZorasDomainPointNameENGTex": "Βασίλειον τῶν Ζῶρα",
    # 22 World Map Position Names (80x32 ia8)
    "gHyruleFieldPositionNameENGTex": "Πεδίον Ὑρούλης",
    "gKakarikoVillagePositionNameENGTex": "Κώμη Κακαρικό",
    "gGraveyardPositionNameENGTex": "Κοιμητήριον",
    "gZorasRiverPositionNameENGTex": "Ποταμὸς Ζῶρα",
    "gKokiriForestPositionNameENGTex": "Δρυμὸς Κοκίρι",
    "gSacredForestMeadowPositionNameENGTex": "Ἱερὸς Λειμών",
    "gLakeHyliaPositionNameENGTex": "Λίμνη Ὑλία",
    "gZorasDomainPositionNameENGTex": "Βασίλειον Ζῶρα",
    "gZorasFountainPositionNameENGTex": "Πηγὴ τῶν Ζῶρα",
    "gGerudoValleyPositionNameENGTex": "Φάραγξ Γερούδων",
    "gLostWoodsPositionNameENGTex": "Δρυμὸς Πλάνης",
    "gDesertColossusPositionNameENGTex": "Κολοσσὸς Ἐρήμου",
    "gGerudosFortressPositionNameENGTex": "Ὀχύρωμα Γερούδων",
    "gHauntedWastelandPositionNameENGTex": "Ἔρημος Φαντασμάτων",
    "gMarketPositionNameENGTex": "Ἀγορά",
    "gHyruleCastlePositionNameENGTex": "Φρούριον Ὑρούλης",
    "gDeathMountainTrailPositionNameENGTex": "Ἀτραπὸς Ὄρους",
    "gDeathMountainCraterPositionNameENGTex": "Κρατὴρ Ὄρους",
    "gGoronCityPositionNameENGTex": "Πόλις Γορώνων",
    "gLonLonRanchPositionNameENGTex": "Ἔπαυλις Λὸν Λόν",
    "gQuestionMarkPositionNameENGTex": ";",
    "gGanonsCastlePositionNameENGTex": "Φρούριον Γάνωνος",
}


# ==============================================================================
# 2. Rendering & Texture Encoders
# ==============================================================================

def create_text_texture(text: str, width: int, height: int, start_size: int = 12, max_text_width: int = None) -> Image.Image:
    """Renders text dynamically scaled to fit within (width, height) with authentic drop-shadow."""
    size = start_size
    target_max_w = min(width - 4, max_text_width) if max_text_width else (width - 4)
    while size > 7:
        font = ImageFont.truetype(FONT_PATH, size)
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if tw <= target_max_w and th <= height - 2:
            break
        size -= 1

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = (width - tw) // 2 - bbox[0]
    y = (height - th) // 2 - bbox[1]

    # Draw 1px drop shadow / outline in black
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1), (0, 2), (1, 2)]:
        draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 255))

    # Draw white text
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    return img


def encode_ia4(img: Image.Image) -> bytes:
    w, h = img.size
    pixels = img.load()
    out = bytearray()
    for y in range(h):
        for x in range(0, w, 2):
            nibbles = []
            for px in (x, x + 1):
                r, g, b, a = pixels[px, y]
                i3 = (r * 7 + 127) // 255
                a1 = 1 if a > 64 else 0
                nib = (i3 << 1) | a1
                nibbles.append(nib & 0xF)
            out.append((nibbles[0] << 4) | nibbles[1])
    return bytes(out)


def decode_ia8(data: bytes, w: int, h: int) -> Image.Image:
    im = Image.new("RGBA", (w, h))
    pixels = im.load()
    idx = 0
    for y in range(h):
        for x in range(w):
            b = data[idx]
            idx += 1
            i = (b >> 4) & 0xF
            a = b & 0xF
            i8 = (i * 255) // 15
            a8 = (a * 255) // 15
            pixels[x, y] = (i8, i8, i8, a8)
    return im


def carve_stone_text(bg: Image.Image, text: str, size: int = 11) -> Image.Image:
    out = bg.copy()
    draw = ImageDraw.Draw(out)
    font = ImageFont.truetype(FONT_PATH, size)
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    w, h = bg.size
    x = (w - tw) // 2 - bbox[0]
    # Stone beam is rows 4..18 (15 rows, height 14 from 4 to 18)
    y = 4 + (14 - th) // 2 - bbox[1]

    # Draw bottom-right highlight (light from top-left)
    draw.text((x + 1, y + 1), text, font=font, fill=(240, 240, 240, 255))
    # Draw top-left shadow
    draw.text((x - 1, y - 1), text, font=font, fill=(30, 30, 30, 255))
    # Draw main groove (carved dark)
    draw.text((x, y), text, font=font, fill=(10, 10, 10, 255))
    return out


def synthesize_clean_banner_beam(im_00: Image.Image, im_10_orig: Image.Image, im_20: Image.Image) -> Image.Image:
    """Synthesizes a 100% clean stone beam (rows 4..18) across the full 80px tile width
    using authentic stone textures from im_00 and im_20, perfectly blending with top and bottom bevels."""
    out = np.array(im_10_orig, dtype=np.float32)
    arr_00 = np.array(im_00, dtype=np.float32)
    arr_20 = np.array(im_20, dtype=np.float32)

    # In im_00, x=20..80 (60 px) is pure clean stone beam
    # In im_20, x=0..60 (60 px) is pure clean stone beam
    stone_00 = arr_00[4:19, 20:80]  # shape (15, 60)
    stone_20 = arr_20[4:19, 0:60]   # shape (15, 60)

    beam = np.zeros((15, 80, 4), dtype=np.float32)

    # 40px smooth cosine cross-fade in the center (x=20..60)
    w = np.linspace(0.0, 1.0, 40)
    w = 0.5 * (1.0 - np.cos(np.pi * w))
    w = w.reshape(1, 40, 1)

    beam[:, 0:20] = stone_00[:, 0:20]
    beam[:, 20:60] = (1.0 - w) * stone_00[:, 20:60] + w * stone_20[:, 0:40]
    beam[:, 60:80] = stone_20[:, 40:60]

    # Feather top and bottom rows (y=4 and y=18) by 50% with original bevels for zero edge artifact
    out[4] = 0.5 * out[4] + 0.5 * beam[0]
    out[5:18] = beam[1:14]
    out[18] = 0.5 * out[18] + 0.5 * beam[14]

    # Guarantee full opacity across the tile
    out[:, :, 3] = 255.0
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def patch_pause_menu_banners(bin_path: str, base_rom_path: str = os.path.join("oot", "baseroms", "ntsc-1.2", "baserom-decompressed.z64")):
    """Patches all 9 pause menu banner tiles in icon_item_nes_static with seamless
    solid stone backgrounds and cleanly engraved Greek titles, eliminating all box seams and residual artifacts."""
    if not os.path.exists(bin_path) or not os.path.exists(base_rom_path):
        print(f"[-] Cannot patch pause menu banners: missing {bin_path} or {base_rom_path}")
        return

    with open(base_rom_path, "rb") as f_rom:
        rom = f_rom.read()
    with open(bin_path, "rb") as f_bin:
        bin_data = bytearray(f_bin.read())

    base_static = 0x007BD000
    base_jpn    = 0x00864000
    base_nes    = 0x00872000

    # 1. Equipment (offset 0x8280) -> Tile 10
    im_eq_00 = decode_ia8(rom[base_static + 0x5C3C0 : base_static + 0x5C3C0 + 2560], 80, 32)
    im_eq_10 = decode_ia8(rom[base_nes + 0x8280 : base_nes + 0x8280 + 2560], 80, 32)
    im_eq_20 = decode_ia8(rom[base_static + 0x5CDC0 : base_static + 0x5CDC0 + 2560], 80, 32)
    clean_eq_10 = synthesize_clean_banner_beam(im_eq_00, im_eq_10, im_eq_20)
    bin_data[0x8280 : 0x8280 + 2560] = encode_ia8(carve_stone_text(clean_eq_10, "Ἐξοπλισμός", size=10))

    # 2. Select Item 00, 10, 20 (offsets 0x8C80, 0x9680, 0xA080)
    im_si_00 = decode_ia8(rom[base_jpn + 0x8C80 : base_jpn + 0x8C80 + 2560], 80, 32)
    im_si_10 = decode_ia8(rom[base_nes + 0x9680 : base_nes + 0x9680 + 2560], 80, 32)
    im_si_20 = decode_ia8(rom[base_jpn + 0xA080 : base_jpn + 0xA080 + 2560], 80, 32)
    clean_si_10 = synthesize_clean_banner_beam(im_si_00, im_si_10, im_si_20)
    bin_data[0x8C80 : 0x8C80 + 2560] = encode_ia8(im_si_00)
    bin_data[0x9680 : 0x9680 + 2560] = encode_ia8(carve_stone_text(clean_si_10, "Σκεύη", size=11))
    bin_data[0xA080 : 0xA080 + 2560] = encode_ia8(im_si_20)

    # 3. Map 10 (offset 0xAA80)
    im_map_00 = decode_ia8(rom[base_static + 0x5D7C0 : base_static + 0x5D7C0 + 2560], 80, 32)
    im_map_10 = decode_ia8(rom[base_nes + 0xAA80 : base_nes + 0xAA80 + 2560], 80, 32)
    im_map_20 = decode_ia8(rom[base_static + 0x5E1C0 : base_static + 0x5E1C0 + 2560], 80, 32)
    clean_map_10 = synthesize_clean_banner_beam(im_map_00, im_map_10, im_map_20)
    bin_data[0xAA80 : 0xAA80 + 2560] = encode_ia8(carve_stone_text(clean_map_10, "Χάρτης", size=11))

    # 4. Quest Status 00, 10, 20 (offsets 0xB480, 0xBE80, 0xC880)
    im_qs_00 = decode_ia8(rom[base_jpn + 0xB480 : base_jpn + 0xB480 + 2560], 80, 32)
    im_qs_10 = decode_ia8(rom[base_nes + 0xBE80 : base_nes + 0xBE80 + 2560], 80, 32)
    im_qs_20 = decode_ia8(rom[base_jpn + 0xC880 : base_jpn + 0xC880 + 2560], 80, 32)
    clean_qs_10 = synthesize_clean_banner_beam(im_qs_00, im_qs_10, im_qs_20)
    bin_data[0xB480 : 0xB480 + 2560] = encode_ia8(im_qs_00)
    bin_data[0xBE80 : 0xBE80 + 2560] = encode_ia8(carve_stone_text(clean_qs_10, "Ἀγών", size=11))
    bin_data[0xC880 : 0xC880 + 2560] = encode_ia8(im_qs_20)

    # 5. Save 10 (offset 0xD280)
    im_save_00 = decode_ia8(rom[base_static + 0x5EBC0 : base_static + 0x5EBC0 + 2560], 80, 32)
    im_save_10 = decode_ia8(rom[base_nes + 0xD280 : base_nes + 0xD280 + 2560], 80, 32)
    im_save_20 = decode_ia8(rom[base_static + 0x5F5C0 : base_static + 0x5F5C0 + 2560], 80, 32)
    clean_save_10 = synthesize_clean_banner_beam(im_save_00, im_save_10, im_save_20)
    bin_data[0xD280 : 0xD280 + 2560] = encode_ia8(carve_stone_text(clean_save_10, "Σῶσαι", size=11))

    with open(bin_path, "wb") as f_out:
        f_out.write(bin_data)

    print(f"[+] Successfully patched 9 seamless stone pause menu banners into {bin_path}")


def encode_ia8(img: Image.Image) -> bytes:
    w, h = img.size
    pixels = img.load()
    out = bytearray()
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            i4 = (r * 15 + 127) // 255
            a4 = (a * 15 + 127) // 255
            out.append(((i4 & 0xF) << 4) | (a4 & 0xF))
    return bytes(out)


def encode_ia16(img: Image.Image) -> bytes:
    w, h = img.size
    pixels = img.load()
    out = bytearray()
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            out.append(r)
            out.append(a)
    return bytes(out)


def encode_i4(img: Image.Image) -> bytes:
    w, h = img.size
    pixels = img.load()
    out = bytearray()
    for y in range(h):
        for x in range(0, w, 2):
            nibbles = []
            for px in (x, x + 1):
                r, g, b, a = pixels[px, y]
                i4 = (r * 15 + 127) // 255
                nibbles.append(i4 & 0xF)
            out.append((nibbles[0] << 4) | nibbles[1])
    return bytes(out)


def encode_texture(img: Image.Image, fmt: str) -> bytes:
    if fmt == "ia4":
        return encode_ia4(img)
    elif fmt == "ia8":
        return encode_ia8(img)
    elif fmt == "ia16":
        return encode_ia16(img)
    elif fmt == "i4":
        return encode_i4(img)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


# ==============================================================================
# 3. Patching Execution
# ==============================================================================

import xml.etree.ElementTree as ET

def patch_segment_textures(xml_path: str, bin_path: str, trans_map: Dict[str, str], default_start_size: int = 12, max_text_width: int = None) -> int:
    """Patches all English textures defined in xml_path into the binary file at bin_path."""
    if not os.path.exists(bin_path):
        print(f"[-] Segment binary not found: {bin_path}")
        return 0

    tree = ET.parse(xml_path)
    with open(bin_path, "rb") as f:
        data = bytearray(f.read())

    patched_count = 0
    for elem in tree.findall(".//Texture"):
        name = elem.attrib.get("Name", "")
        if name in trans_map:
            greek_text = trans_map[name]
            fmt = elem.attrib.get("Format", "")
            w = int(elem.attrib.get("Width", 0))
            h = int(elem.attrib.get("Height", 0))
            offset = int(elem.attrib.get("Offset", "0"), 16)

            start_sz = default_start_size
            if h <= 12:
                start_sz = 9
            elif h >= 24:
                start_sz = 16

            img = create_text_texture(greek_text, w, h, start_size=start_sz, max_text_width=max_text_width)
            tex_bytes = encode_texture(img, fmt)

            data[offset : offset + len(tex_bytes)] = tex_bytes
            patched_count += 1

    with open(bin_path, "wb") as f:
        f.write(data)

    print(f"[+] Patched {patched_count} Greek textures into {bin_path}")
    return patched_count


def patch_all_menu_textures(rom_path: str = "oot_ancient_greek.z64"):
    """Patches all UI texture categories into baserom extracted files and updates the ROM."""
    print("=== Patching Graphical Menu Textures ===")

    # 1. do_action_static (HUD A-button action icons, max_text_width=30 to prevent HUD overlap)
    patch_segment_textures(
        "oot/assets/xml/textures/do_action_static.xml",
        "oot/extracted/ntsc-1.2/baserom/do_action_static",
        DO_ACTION_MAP,
        default_start_size=11,
        max_text_width=30,
    )

    # 2. icon_item_nes_static (Pause subscreen headers & prompts)
    patch_segment_textures(
        "oot/assets/xml/textures/icon_item_nes_static.xml",
        "oot/extracted/ntsc-1.2/baserom/icon_item_nes_static",
        ICON_ITEM_NES_MAP,
        default_start_size=12,
    )
    # 2b. Solid stone pause menu banners (Equipment, Select Item, Map, Quest Status, Save)
    patch_pause_menu_banners("oot/extracted/ntsc-1.2/baserom/icon_item_nes_static")

    # 3. item_name_static (All 112 inventory and equipment item name banners)
    patch_segment_textures(
        "oot/assets/xml/textures/item_name_static.xml",
        "oot/extracted/ntsc-1.2/baserom/item_name_static",
        ITEM_NAME_MAP,
        default_start_size=12,
    )

    # 4. map_name_static (World map point names and area position names)
    patch_segment_textures(
        "oot/assets/xml/textures/map_name_static.xml",
        "oot/extracted/ntsc-1.2/baserom/map_name_static",
        MAP_NAME_MAP,
        default_start_size=12,
    )

    # 5. title_static (File select screen & options)
    patch_segment_textures(
        "oot/assets/xml/textures/title_static.xml",
        "oot/extracted/ntsc-1.2/baserom/title_static",
        TITLE_STATIC_MAP,
        default_start_size=12,
    )

    # 6. place_title_cards (Area entrance calligraphy title cards)
    tree_place = ET.parse("oot/assets/xml/textures/place_title_cards.xml")
    place_patched = 0
    for f_elem in tree_place.findall(".//File"):
        fname = f_elem.attrib["Name"]
        bin_file = os.path.join("oot", "extracted", "ntsc-1.2", "baserom", fname)
        if not os.path.exists(bin_file):
            continue
        with open(bin_file, "rb") as bf:
            bdata = bytearray(bf.read())
        for tex in f_elem.findall(".//Texture"):
            tname = tex.attrib["Name"]
            if tname in PLACE_TITLE_MAP:
                gtxt = PLACE_TITLE_MAP[tname]
                w = int(tex.attrib["Width"])
                h = int(tex.attrib["Height"])
                off = int(tex.attrib["Offset"], 16)
                t_img = create_text_texture(gtxt, w, h, start_size=16)
                t_b = encode_texture(t_img, "ia8")
                bdata[off : off + len(t_b)] = t_b
                place_patched += 1
        with open(bin_file, "wb") as bf:
            bf.write(bdata)
    print(f"[+] Patched {place_patched} Greek title cards into baserom place cards")

    # Now inject these patched segments directly into the target playable ROM!
    if os.path.exists(rom_path):
        with open(rom_path, "rb") as f:
            rom = bytearray(f.read())

        # Offsets in decompressed ROM
        ROM_MAPS = [
            ("oot/extracted/ntsc-1.2/baserom/icon_item_nes_static", 0x00872000),
            ("oot/extracted/ntsc-1.2/baserom/item_name_static", 0x00880000),
            ("oot/extracted/ntsc-1.2/baserom/map_name_static", 0x008BE000),
            ("oot/extracted/ntsc-1.2/baserom/do_action_static", 0x008E0000),
            ("oot/extracted/ntsc-1.2/baserom/title_static", 0x01A02000),
        ]

        for bpath, rom_addr in ROM_MAPS:
            with open(bpath, "rb") as f:
                seg_bytes = f.read()
            rom[rom_addr : rom_addr + len(seg_bytes)] = seg_bytes
            print(f"[+] Injected {os.path.basename(bpath)} ({len(seg_bytes):,} bytes) at 0x{rom_addr:08X} in ROM")

        # Inject place title cards (g_pn_01 to g_pn_57)
        # From dmadata (0x0B060): g_pn_01 starts at 0x0198A000, each card spaced by 0x2000
        for i in range(1, 58):
            pname = f"g_pn_{i:02d}"
            pfile = os.path.join("oot", "extracted", "ntsc-1.2", "baserom", pname)
            if os.path.exists(pfile):
                with open(pfile, "rb") as pf:
                    pbytes = pf.read()
                r_addr = 0x0198A000 + (i - 1) * 0x2000
                rom[r_addr : r_addr + len(pbytes)] = pbytes

        print(f"[+] Injected 57 place title card segments into ROM")

        # Recalculate checksum (CIC-6105)
        print("[+] Recalculating N64 header checksum (CIC-6105)...")
        crc = ipl3checksum.CICKind.CIC_X105.calculateChecksum(bytes(rom))
        rom[0x10:0x18] = struct.pack(">II", crc[0], crc[1])
        print(f"[+] Checksum updated: CRC1 = 0x{crc[0]:08X}, CRC2 = 0x{crc[1]:08X}")

        with open(rom_path, "wb") as f:
            f.write(rom)

        print(f"[+] SUCCESS: Fully updated ROM with Greek menus at: {rom_path}")


if __name__ == "__main__":
    patch_all_menu_textures()
