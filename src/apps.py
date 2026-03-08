"""
Multi-niche app registry — single source of truth for tracked apps.

Niches:
  💑  Couple & Relationships
  🚭  Smoking Cessation
  🧠  AI Psychologist & Mental Health
  🌿  AI Plant Scanner
  🍎  Calorie & Nutrition Tracker

Add new apps here — the scraper, dashboard, and reports all read from this list.
"""

from __future__ import annotations

from src.models import AppConfig, AppNiche

# ═══════════════════════════════════════════════════════════════════════════
#  💑  COUPLE & RELATIONSHIPS
#  Все приложения, о которых говорят на Reddit:
#  - пары / тесты для пар / квизы / виджеты
#  - long-distance / date night
#  - AI-отношения, совместимость, Love Language
# ═══════════════════════════════════════════════════════════════════════════

_COUPLE_APPS: list[AppConfig] = [
    AppConfig(
        name="Couple Joy",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["couple joy app", "couplejoy", '"couple joy"'],
        aliases=["couplejoy", "couple joy"],
    ),
    AppConfig(
        name="Paired",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=['"paired app"', '"paired" couple app', "paired relationship app"],
        aliases=["paired app", "paired couple", "getpaired"],
    ),
    AppConfig(
        name="Between",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=['"between app" couple', '"between" relationship app'],
        aliases=["between app"],
    ),
    AppConfig(
        name="Lovewick",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["lovewick", "lovewick app"],
        aliases=["lovewick", "love wick"],
    ),
    AppConfig(
        name="Love Nudge",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=['"love nudge"', '"love nudge" app'],
        aliases=["love nudge", "lovenudge"],
    ),
    AppConfig(
        name="Couply",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["couply app", "couply couple"],
        aliases=["couply"],
    ),
    AppConfig(
        name="Lasting",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=['"lasting app"', '"lasting" marriage app'],
        aliases=["lasting app"],
    ),
    AppConfig(
        name="Honeydue",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["honeydue", "honeydue app"],
        aliases=["honeydue", "honey due"],
    ),
    AppConfig(
        name="Happy Couple",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=['"happy couple" app', "happycouple app"],
        aliases=["happy couple app", "happycouple"],
    ),
    # ── NEW: popular on Reddit ──
    AppConfig(
        name="Gottman Card Decks",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["gottman app", "gottman card decks", '"gottman" couple app'],
        aliases=["gottman", "gottman card"],
    ),
    AppConfig(
        name="Widgetable",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["widgetable couple", "widgetable app"],
        aliases=["widgetable"],
    ),
    AppConfig(
        name="Locket Widget",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["locket widget", "locket app couple"],
        aliases=["locket widget", "locket app", "locket"],
    ),
    AppConfig(
        name="NoteIt",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["noteit widget", "noteit couple app"],
        aliases=["noteit", "note it widget"],
    ),
    AppConfig(
        name="Tuned",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["tuned app couple", "tuned facebook couple"],
        aliases=["tuned app", "tuned couple"],
    ),
    AppConfig(
        name="Kindu",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["kindu app", "kindu couple"],
        aliases=["kindu"],
    ),
    AppConfig(
        name="iPassion",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["ipassion app", "ipassion couple"],
        aliases=["ipassion"],
    ),
    AppConfig(
        name="Relish",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["relish relationship app", "relish couple coaching"],
        aliases=["relish app", "relish relationship"],
    ),
    AppConfig(
        name="Coral",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["coral intimacy app", "coral sexual wellness"],
        aliases=["coral app", "coral intimacy"],
    ),
    AppConfig(
        name="Ritual",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["ritual couple app", "ritual relationship app"],
        aliases=["ritual couple", "ritual app couple"],
    ),
    AppConfig(
        name="Us Two",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["us two app", "ustwo couple app"],
        aliases=["us two", "ustwo"],
    ),
    AppConfig(
        name="Dipsea",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["dipsea app", "dipsea stories couple"],
        aliases=["dipsea"],
    ),
    AppConfig(
        name="Esther Perel",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["esther perel app", "esther perel where should we begin"],
        aliases=["esther perel"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  🚭  SMOKING CESSATION
#  Бросание курить + бросание vaping + зависимости
#  Allen Carr часто обсуждается — не приложение, но метод → ищем как контекст
# ═══════════════════════════════════════════════════════════════════════════

_SMOKING_APPS: list[AppConfig] = [
    AppConfig(
        name="Smoke Free",
        niche=AppNiche.SMOKING,
        search_queries=['"smoke free" app', "smokefree app", "smoke free quit"],
        aliases=["smoke free", "smokefree"],
    ),
    AppConfig(
        name="QuitNow!",
        niche=AppNiche.SMOKING,
        search_queries=["quitnow app", '"quit now" smoking app'],
        aliases=["quitnow", "quit now"],
    ),
    AppConfig(
        name="Kwit",
        niche=AppNiche.SMOKING,
        search_queries=["kwit app", "kwit quit smoking"],
        aliases=["kwit"],
    ),
    AppConfig(
        name="EasyQuit",
        niche=AppNiche.SMOKING,
        search_queries=["easyquit app", "easy quit smoking"],
        aliases=["easyquit", "easy quit"],
    ),
    AppConfig(
        name="QuitGenius",
        niche=AppNiche.SMOKING,
        search_queries=["quit genius app", "quitgenius"],
        aliases=["quit genius", "quitgenius"],
    ),
    AppConfig(
        name="Flamy",
        niche=AppNiche.SMOKING,
        search_queries=["flamy app", "flamy quit smoking"],
        aliases=["flamy"],
    ),
    # ── NEW: popular on Reddit ──
    AppConfig(
        name="Grounded",
        niche=AppNiche.SMOKING,
        search_queries=["grounded quit smoking app", "grounded app addiction"],
        aliases=["grounded app", "grounded quit"],
    ),
    AppConfig(
        name="I Am Sober",
        niche=AppNiche.SMOKING,
        search_queries=["i am sober app", "iamsober app quit"],
        aliases=["i am sober", "iamsober"],
    ),
    AppConfig(
        name="QuitSure",
        niche=AppNiche.SMOKING,
        search_queries=["quitsure app", "quit sure smoking"],
        aliases=["quitsure", "quit sure"],
    ),
    AppConfig(
        name="Quitzilla",
        niche=AppNiche.SMOKING,
        search_queries=["quitzilla app", "quitzilla quit smoking"],
        aliases=["quitzilla"],
    ),
    AppConfig(
        name="Quit Vaping / QuitGo",
        niche=AppNiche.SMOKING,
        search_queries=["quit vaping app", "quitgo app", "quit vape app"],
        aliases=["quit vaping", "quitgo", "quit vape"],
    ),
    AppConfig(
        name="LIVESTRONG MyQuit Coach",
        niche=AppNiche.SMOKING,
        search_queries=["livestrong myquit coach", "livestrong quit smoking"],
        aliases=["livestrong", "myquit coach"],
    ),
    AppConfig(
        name="Nomo",
        niche=AppNiche.SMOKING,
        search_queries=["nomo sobriety app", "nomo quit smoking"],
        aliases=["nomo app", "nomo sobriety"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  🧠  AI PSYCHOLOGIST & MENTAL HEALTH
#  AI-терапия, CBT-боты, медитация, mindfulness, mood-трекеры,
#  онлайн-терапия (BetterHelp/Talkspace), виджеты ментального здоровья
# ═══════════════════════════════════════════════════════════════════════════

_AI_PSYCH_APPS: list[AppConfig] = [
    AppConfig(
        name="Breeze",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=['"breeze" therapy app', '"breeze" mental health app'],
        aliases=["breeze app", "breeze therapy"],
    ),
    AppConfig(
        name="Headspace",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["headspace app", "headspace meditation"],
        aliases=["headspace"],
    ),
    AppConfig(
        name="Woebot",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["woebot app", "woebot ai therapy"],
        aliases=["woebot"],
    ),
    AppConfig(
        name="Wysa",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["wysa app", "wysa ai therapist"],
        aliases=["wysa"],
    ),
    AppConfig(
        name="Youper",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["youper app", "youper ai"],
        aliases=["youper"],
    ),
    AppConfig(
        name="Calm",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["calm app review", "calm meditation app"],
        aliases=["calm app"],
    ),
    AppConfig(
        name="BetterHelp",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["betterhelp app", "betterhelp review"],
        aliases=["betterhelp", "better help"],
    ),
    AppConfig(
        name="Talkspace",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["talkspace app", "talkspace review"],
        aliases=["talkspace", "talk space"],
    ),
    # ── NEW: popular on Reddit ──
    AppConfig(
        name="Replika",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["replika app", "replika ai companion", "replika mental health"],
        aliases=["replika"],
    ),
    AppConfig(
        name="7 Cups",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["7 cups app", "7cups therapy", "seven cups of tea"],
        aliases=["7 cups", "7cups", "seven cups"],
    ),
    AppConfig(
        name="Sanvello",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["sanvello app", "sanvello cbt anxiety"],
        aliases=["sanvello"],
    ),
    AppConfig(
        name="Happify",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["happify app", "happify mental health"],
        aliases=["happify"],
    ),
    AppConfig(
        name="Daylio",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["daylio app", "daylio mood tracker"],
        aliases=["daylio"],
    ),
    AppConfig(
        name="Finch",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["finch self care app", "finch mental health"],
        aliases=["finch app", "finch self care"],
    ),
    AppConfig(
        name="Bearable",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["bearable app", "bearable health tracker"],
        aliases=["bearable"],
    ),
    AppConfig(
        name="Insight Timer",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["insight timer app", "insight timer meditation"],
        aliases=["insight timer"],
    ),
    AppConfig(
        name="Earkick",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["earkick app", "earkick ai anxiety"],
        aliases=["earkick"],
    ),
    AppConfig(
        name="Bloom",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["bloom cbt app", "bloom therapy app"],
        aliases=["bloom app", "bloom therapy", "bloom cbt"],
    ),
    AppConfig(
        name="Stoic",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["stoic mental health app", "stoic mood journal"],
        aliases=["stoic app", "stoic journal"],
    ),
    AppConfig(
        name="MindShift CBT",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["mindshift cbt app", "mindshift anxiety app"],
        aliases=["mindshift", "mind shift"],
    ),
    AppConfig(
        name="Endel",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["endel app", "endel ai soundscapes"],
        aliases=["endel"],
    ),
    AppConfig(
        name="Reflectly",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["reflectly app", "reflectly ai journal"],
        aliases=["reflectly"],
    ),
    AppConfig(
        name="MoodPath / MindDoc",
        niche=AppNiche.RELATIONSHIPS,
        search_queries=["moodpath app", "minddoc app", "moodpath depression"],
        aliases=["moodpath", "minddoc", "mind doc"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  🌿  AI PLANT SCANNER
#  Определение растений, уход, AI-чат про растения, грибы, деревья
# ═══════════════════════════════════════════════════════════════════════════

_PLANT_APPS: list[AppConfig] = [
    AppConfig(
        name="PictureThis",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["picturethis app", "picturethis plant"],
        aliases=["picturethis", "picture this"],
    ),
    AppConfig(
        name="PlantNet",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["plantnet app", "pl@ntnet"],
        aliases=["plantnet", "pl@ntnet", "plant net"],
    ),
    AppConfig(
        name="Planta",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["planta app", "planta plant care"],
        aliases=["planta app", "planta plant"],
    ),
    AppConfig(
        name="LeafSnap",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["leafsnap app", "leaf snap plant"],
        aliases=["leafsnap", "leaf snap"],
    ),
    AppConfig(
        name="Blossom",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["blossom plant app", "blossom plant care"],
        aliases=["blossom plant", "blossom app"],
    ),
    AppConfig(
        name="Greg",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=['"greg" plant app', '"greg" plant care app'],
        aliases=["greg plant", "greg app"],
    ),
    # ── NEW: popular on Reddit ──
    AppConfig(
        name="iNaturalist",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["inaturalist app", "inaturalist plant identification"],
        aliases=["inaturalist", "i naturalist"],
    ),
    AppConfig(
        name="Seek by iNaturalist",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["seek app plant", "seek inaturalist"],
        aliases=["seek app", "seek inaturalist", "seek by inaturalist"],
    ),
    AppConfig(
        name="PlantIn",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["plantin app", "plantin plant identifier"],
        aliases=["plantin"],
    ),
    AppConfig(
        name="Flora Incognita",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["flora incognita app", "flora incognita plant"],
        aliases=["flora incognita"],
    ),
    AppConfig(
        name="SmartPlant",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["smartplant app", "smart plant identifier"],
        aliases=["smartplant", "smart plant"],
    ),
    AppConfig(
        name="Garden Answers",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["garden answers app", "garden answers plant"],
        aliases=["garden answers"],
    ),
    AppConfig(
        name="NatureID",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["natureid app", "nature id plant identifier"],
        aliases=["natureid", "nature id"],
    ),
    AppConfig(
        name="PlantSnap",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["plantsnap app", "plant snap identifier"],
        aliases=["plantsnap", "plant snap"],
    ),
    AppConfig(
        name="Garden Tags",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["garden tags app", "gardentags plant"],
        aliases=["garden tags", "gardentags"],
    ),
    AppConfig(
        name="ShroomID",
        niche=AppNiche.PLANT_SCANNER,
        search_queries=["shroomid app", "mushroom identifier app"],
        aliases=["shroomid", "shroom id", "mushroom id"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  🍎  CALORIE & NUTRITION TRACKER
#  Всё про калории, макросы, food logging, AI сканеры еды,
#  весовые трекеры, диеты (CICO, IF), фитнес-часы + трекеры
# ═══════════════════════════════════════════════════════════════════════════

_CALORIE_APPS: list[AppConfig] = [
    AppConfig(
        name="MyFitnessPal",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["myfitnesspal app", "myfitnesspal review"],
        aliases=["myfitnesspal", "my fitness pal"],
    ),
    AppConfig(
        name="Lose It!",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["lose it app", "loseit calorie"],
        aliases=["lose it", "loseit"],
    ),
    AppConfig(
        name="CalAI",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["calai app", "cal ai calorie"],
        aliases=["calai", "cal ai"],
    ),
    AppConfig(
        name="Cronometer",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["cronometer app", "cronometer nutrition"],
        aliases=["cronometer"],
    ),
    AppConfig(
        name="Yazio",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["yazio app", "yazio calorie"],
        aliases=["yazio"],
    ),
    AppConfig(
        name="MacroFactor",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["macrofactor app", "macro factor"],
        aliases=["macrofactor", "macro factor"],
    ),
    AppConfig(
        name="FatSecret",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["fatsecret app", "fat secret calorie"],
        aliases=["fatsecret", "fat secret"],
    ),
    # ── NEW: popular on Reddit ──
    AppConfig(
        name="Noom",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["noom app", "noom calorie tracker", "noom weight loss"],
        aliases=["noom"],
    ),
    AppConfig(
        name="Lifesum",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["lifesum app", "lifesum calorie tracker"],
        aliases=["lifesum"],
    ),
    AppConfig(
        name="Nutracheck",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["nutracheck app", "nutracheck calorie"],
        aliases=["nutracheck"],
    ),
    AppConfig(
        name="MyNetDiary",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["mynetdiary app", "my net diary calorie"],
        aliases=["mynetdiary", "my net diary"],
    ),
    AppConfig(
        name="MyPlate by Livestrong",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["myplate calorie tracker", "livestrong myplate"],
        aliases=["myplate", "my plate"],
    ),
    AppConfig(
        name="Carb Manager",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["carb manager app", "carbmanager keto"],
        aliases=["carb manager", "carbmanager"],
    ),
    AppConfig(
        name="Healthi (iTrackBites)",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["healthi app", "itrackbites app", "healthi calorie"],
        aliases=["healthi", "itrackbites"],
    ),
    AppConfig(
        name="Nutritionix Track",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["nutritionix app", "nutritionix track calorie"],
        aliases=["nutritionix"],
    ),
    AppConfig(
        name="Foodvisor",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["foodvisor app", "foodvisor ai calorie"],
        aliases=["foodvisor"],
    ),
    AppConfig(
        name="Happy Scale",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["happy scale app", "happy scale weight tracker"],
        aliases=["happy scale"],
    ),
    AppConfig(
        name="Fastic",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["fastic app", "fastic fasting tracker"],
        aliases=["fastic"],
    ),
    AppConfig(
        name="RP Diet",
        niche=AppNiche.CALORIE_TRACKER,
        search_queries=["rp diet app", "rp strength diet"],
        aliases=["rp diet", "rp strength"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  FULL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

TRACKED_APPS: list[AppConfig] = (
    _COUPLE_APPS + _SMOKING_APPS + _AI_PSYCH_APPS + _PLANT_APPS + _CALORIE_APPS
)

# ── Generic queries per niche (Strategy 2 in scraper) ────────────────────

GENERIC_QUERIES: dict[AppNiche, list[str]] = {
    AppNiche.RELATIONSHIPS: [
        # Couples & Relationships
        "best couple app",
        "couple app recommendation",
        "best app for couples relationship",
        "app for couples long distance",
        "relationship app review",
        "couple quiz app",
        "couple game app",
        "couple widget app",
        "date night app",
        "love language test app",
        "couples therapy app",
        "long distance relationship app",
        "intimacy app for couples",
        # AI Therapy & Mental Health
        "best ai therapy app",
        "ai psychologist app",
        "mental health app review",
        "ai therapist chatbot app",
        "meditation app recommendation",
        "best cbt app anxiety",
        "mood tracker app",
        "ai counselor app",
        "mindfulness app review",
        "online therapy app review",
        "depression app recommendation",
        "anxiety self help app",
        "journaling mental health app",
    ],
    AppNiche.SMOKING: [
        "best quit smoking app",
        "app to stop smoking",
        "smoking cessation app review",
        "nicotine free app",
        "quit vaping app",
        "best app to quit nicotine",
        "stop smoking tracker",
        "quit smoking cold turkey app",
        "addiction recovery app smoking",
        "Allen Carr app",
    ],
    AppNiche.PLANT_SCANNER: [
        "best plant identifier app",
        "ai plant scanner app",
        "plant identification app review",
        "plant care app recommendation",
        "best app to identify plants",
        "free plant identifier",
        "mushroom identifier app",
        "tree identification app",
        "garden planner app",
        "houseplant care app",
    ],
    AppNiche.CALORIE_TRACKER: [
        "best calorie tracker app",
        "calorie counting app review",
        "nutrition tracker app recommendation",
        "food logging app",
        "best macro tracking app",
        "ai food scanner calorie app",
        "barcode scanner calorie app",
        "best free calorie counter",
        "intermittent fasting tracker app",
        "weight loss tracker app",
        "food diary app recommendation",
        "CICO app recommendation",
    ],
}

# Flatten for backward compatibility
GENERIC_QUERIES_FLAT: list[str] = [q for qs in GENERIC_QUERIES.values() for q in qs]


# ── Lookup helpers ───────────────────────────────────────────────────────


def get_app_by_name(name: str) -> AppConfig | None:
    """Look up an app config by exact name (case-insensitive)."""
    name_lower = name.lower()
    for app in TRACKED_APPS:
        if app.name.lower() == name_lower:
            return app
    return None


def get_apps_by_niche(niche: AppNiche) -> list[AppConfig]:
    """Return all apps in a given niche."""
    return [a for a in TRACKED_APPS if a.niche == niche]


def get_all_app_names() -> list[str]:
    """Return all tracked app names."""
    return [app.name for app in TRACKED_APPS]


def get_all_niches() -> list[AppNiche]:
    """Return all niches that have at least one tracked app."""
    return list({a.niche for a in TRACKED_APPS})
