# -*- coding: utf-8 -*-
"""Red-flag clause rule registry — bilingual (Arabic + English).

Declarative rules: patterns matched inside a clause (mode "any"/"all"),
an honest heuristic severity, which party the term usually harms (`side`),
a plain-language explanation, and a FAIR COUNTER-CLAUSE template in both
languages for the human to adapt.

Arabic patterns are written in FOLDED orthography (no tashkeel; ا/ي/ه
unified) because matching goes through clauses.match_any(): raw text
first, Arabic-folded text second.

Bright lines:
  * detection only — never presented as a lawyer's opinion (every report
    carries the not-legal-advice disclaimer)
  * severities are negotiation signals, not proof of enforceability
  * counter-clause text is a TEMPLATE for a human — not a legal outcome
"""
import re

SEVERITIES = ("high", "medium", "low", "info")
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1, "info": 0}


class Rule(object):
    __slots__ = ("id", "severity", "category", "side", "title_en",
                 "title_ar", "patterns", "mode", "why_en", "why_ar",
                 "fix_en", "fix_ar", "_compiled")

    def __init__(self, id, severity, category, side, title_en, title_ar,
                 patterns, why_en, why_ar, fix_en, fix_ar, mode="any"):
        assert severity in SEVERITIES, severity
        assert mode in ("any", "all")
        self.id = id
        self.severity = severity
        self.category = category        # ip|money|exit|liability|scope|data
        self.side = side                # provider|client|both
        self.title_en = title_en
        self.title_ar = title_ar
        self.patterns = list(patterns)
        self.mode = mode
        self.why_en = why_en
        self.why_ar = why_ar
        self.fix_en = fix_en
        self.fix_ar = fix_ar
        self._compiled = [re.compile(p, re.I) for p in patterns]

    def as_dict(self):
        return {"id": self.id, "severity": self.severity,
                "category": self.category, "side": self.side,
                "title_en": self.title_en, "title_ar": self.title_ar}


def _r(id, severity, category, side, title_en, title_ar, patterns,
       why_en, why_ar, fix_en, fix_ar, mode="any"):
    return Rule(id, severity, category, side, title_en, title_ar, patterns,
                why_en, why_ar, fix_en, fix_ar, mode)


RULES = [
    _r("LG-IP-PREPAY", "high", "ip", "provider",
       "Work product IP transfers before payment",
       "نقل ملكية الفكر قبل الدفع",
       [r"(intellectual propert|copyright|work product|source code|ملك?يه\s+الفكريه|حقوق\s+المولف|الكود\s+المصدري)",
        r"(assign\w*|transfer\w*|vest\w*|shall\s+own|work\s+made\s+for\s+hire|نقل|تنتقل|تؤول|يملك)",
        r"(advance|upfront|prepay|before.{0,20}pay|prior\s+to\s+payment|قبل|مقدم|مدفوع\w*)"],
       "IP in the deliverables is assigned to the client before (or without) "
       "conditioning on payment — a classic trap: you can lose rights to the "
       "code/design before receiving money.",
       "تنتقل ملكية الفكر في المخرجات للعميل قبل الدفع أو دون ربطها به — فخ "
       "كلاسيكي: قد تخسر حقوقك في الكود/التصميم قبل استلام أي مال.",
       "Each party keeps its pre-existing IP; upon receipt of full payment "
       "Provider assigns the final deliverables' IP to Client, excluding "
       "Provider's pre-existing tools and libraries.",
       "يحتفظ كل طرف بملكية ما قبل التعاقد؛ وعند سداد كامل المبلغ ينقل المقدم "
       "ملكية المخرجات النهائية للعميل، عدا أدوات ومكتبات المقدم القائمة.",
       mode="all"),

    _r("LG-NO-OWNERSHIP", "high", "ip", "client",
       "Client pays but acquires no rights in the work",
       "العميل يدفع ولا يملك العمل",
       [r"shall\s+not\s+(acquire|own|receive|obtain)\w*\s+.{0,40}(right|title|interest|ownership)",
        r"(لا\s+(?:يكتسب|تملك|يملك)|لا\s+تنتقل\s+حقوق|لا\s+يمنح\s+حقوق)"],
       "The paying party funds the work yet receives no rights in it — fees "
       "buy time, not the deliverable. Payment without ownership is a red "
       "flag for the client.",
       "الطرف الدافع يموّل العمل ولا يملك منه حقاً — الأجر يشتري وقتاً لا "
       "مخرجات. الدفع دون ملكية علامة خطر على العميل.",
       "Upon full payment, Client owns the final deliverables; Provider "
       "retains pre-existing materials, generic know-how, and the right to "
       "show the work in a portfolio unless agreed otherwise.",
       "وعند الدفع الكامل يمتلك العميل المخرجات النهائية؛ ويحتفظ المقدم "
       "بمواده القائمة وخبرته العامة وحق عرض العمل في معرض أعماله ما لم "
       "يُتفق على خلاف ذلك."),

    _r("LG-LATE-PENALTY", "medium", "money", "both",
       "Daily or un-capped late payment penalty",
       "غرامة تأخير يومية أو غير محدودة",
       [r"(late|delay)\w*\s+(penalt|fine|charge|fee)",
        r"(penalt|fine|charge).{0,30}(per|each|every)\s+day",
        r"غرامه.{0,25}(يوم|التاخير)|جزاء.{0,25}التاخير|عقوبه.{0,25}يوم|عن\s+كل\s+يوم"],
       "Late fees that run per-day with no cap can snowball past the "
       "contract value. Ask for a cap and a cure/grace period.",
       "غرامات تُحتسب يومياً دون سقف قد تتجاوز قيمة العقد. اطلب سقفاً "
       "وإخطاراً تصحيحياً قبل الغرامة.",
       "Late amounts accrue interest at [X]% per month, capped at [5]% of "
       "the unpaid invoice, and only after 15 days' written notice and a "
       "30-day cure period.",
       "تُحتسب المتأخرات بفائدة [X]% شهرياً بحد أقصى [5]% من قيمة الفاتورة "
       "غير المسددة، وبعد إخطار كتابي بـ 15 يوماً ومهلة تصحيح 30 يوماً."),

    _r("LG-COMPOUND-INTEREST", "medium", "money", "both",
       "Compounding interest on overdue amounts",
       "فائدة مركبة على المتأخرات",
       [r"compound\s+interest", r"interest.{0,25}(accru|compou)",
        r"فائده.{0,25}مركبه|تتراكم.{0,20}شهريا|فائده.{0,20}متزايد"],
       "Compounding (interest on interest) on late amounts grows "
       "exponentially. Prefer simple interest with a cap.",
       "الفائدة المركبة على المتأخرات تنمو أسّياً. الأفضل فائدة بسيطة "
       "بسقف محدّد.",
       "Overdue amounts bear simple interest at [X]% per month (not "
       "compounding), capped at [5]% of the principal.",
       "تُحتسب المتأخرات بفائدة بسيطة [X]% شهرياً (غير مركبة) بحد أقصى "
       "[5]% من الأصل."),

    _r("LG-PAY-NET90", "medium", "money", "provider",
       "Very long payment window (Net 60/90/120+)",
       "نافذة دفع طويلة جداً (60/90/120 يوماً أو أكثر)",
       [r"net\s+(?:45|60|90|120|180)",
        r"payment.{0,40}(forty-five|sixty|ninety|120|180)\s+days?",
        r"(60|90|120|180)\s*(يوم|يوما).{0,30}(بعد|من\s+تاريخ)|دفع.{0,50}(60|90|120)\s*يوم|تسعين\s+يوم"],
       "Net-90 style terms make you finance the client for months; cash "
       "flow often decides which freelancers survive.",
       "شروط مثل Net-90 تجعلك تموّل العميل شهوراً؛ التدفق النقدي غالباً "
       "هو الفارق بين من يصمد ومن ينهار.",
       "Invoices are due within Net [15/30] days of receipt; work on new "
       "milestones pauses on any invoice overdue by more than 30 days.",
       "تُسدَّد الفواتير خلال [15/30] يوماً من استلامها؛ ويُوقَّف العمل على "
       "المراحل الجديدة عند تجاوز أي فاتورة 30 يوم تأخيراً."),

    _r("LG-NONREFUNDABLE", "medium", "money", "client",
       "All payments non-refundable regardless of delivery",
       "جميع المبالغ غير قابلة للاسترداد مهما كان التسليم",
       [r"non-?refundable", r"no\s+refund",
        r"غير\s*قابله?\s*للاسترداد|لا\s+يسترد|غير\s+مسترد"],
       "A blanket non-refund clause removes all leverage if the work is "
       "never delivered or is plainly defective.",
       "بند عدم الاسترداد الشامل يزيل كل ضغط تفاوضي إذا لم يُسلَّم العمل "
       "أو كان معيباً بوضوح.",
       "Fees are non-refundable only for work already delivered and "
       "accepted; if Provider fails to deliver, all advance amounts for "
       "undelivered milestones are returned within 14 days.",
       "لا تُسترد الرسوم إلا عن العمل المسلَّم والمقبول؛ وإذا لم يُسلِّم "
       "المقدم العمل تُعاد مقدمات المراحل غير المسلَّمة خلال 14 يوماً."),

    _r("LG-FINAL-PAY-SUBJECTIVE", "medium", "money", "provider",
       "Final payment hinges on the client's subjective satisfaction",
       "ربط الدفعة الأخيرة بقناعة العميل الذاتية",
       [r"(final|last|remaining)\s+(payment|balance|milestone)|الدفعه\s+(الاخيره|النهائيه)|الرصيد\s+المتبقي",
        r"(sole|satisfact\w+|discretion|قناعه|ارادته|قبول\s+وحده)"],
       "Final payment tied to a party's 'sole satisfaction' is a moving "
       "goalpost — acceptance should be objective (specs + written notice).",
       "ربط الدفعة الأخيرة بـ«قناعة وحده» يجعل الهدف متنقلاً — القبول يجب "
       "أن يكون موضوعياً (مواصفات + إخطار كتابي).",
       "Deliverables are deemed accepted if not rejected in writing within "
       "[10] business days, citing specific non-conformities with the "
       "agreed specifications.",
       "تُعد المخرجات مقبولة إذا لم يُرفض كتابياً خلال [10] أيام عمل مع "
       " بيان مخالفات محددة مقابل المواصفات المتفق عليها.",
       mode="all"),

    _r("LG-AUTORENEW", "low", "money", "both",
       "Automatic renewal without a notice window",
       "تجديد تلقائي دون نافذة إخطار",
       [r"automatically\s+renew", r"renew\w*\s+for\s+(successive|additional|further)",
        r"تجديد.{0,30}تلقائي|يجدد\s+تلقائيا"],
       "Auto-renewals quietly lock you in; without a written opt-out "
       "window you may pay for another full term.",
       "التجديد التلقائي يقيّدك بصمت؛ وبدون نافذة اعتراض كتابية قد تدفع "
       "دورة كاملة إضافية.",
       "This agreement renews only by written mutual consent sent at least "
       "[30] days before term end; either party may decline renewal in "
       "writing without penalty.",
       "يتجدد هذا العقد بموافقة كتابية مشتركة قبل نهاية المدة [30] يوماً "
       "فأكثر؛ ويجوز لأي طرف رفض التجديد كتابياً دون جزاء."),

    _r("LG-UNILATERAL-AMEND", "medium", "exit", "both",
       "Contract can be amended unilaterally",
       "إمكانية تعديل العقد من طرف واحد",
       [r"(may|can|shall)\s+(amend|modify|change)\w*\s+.{0,60}(without\s+(the\s+)?consent|sole\s+discretion|any\s+time|its\s+discretion)",
        r"تعديل.{0,60}(دون\s+موافقه|ارادته|بشكل\s+احادي|وحده)"],
       "A clause letting one party rewrite the deal at any time means "
       "nothing you sign is final.",
       "البند الذي يسمح لطرف بإعادة صياغة الاتفاق في أي وقت يعني أن ما "
       "توقّعه ليس نهائياً.",
       "Any amendment is valid only as a written instrument signed by both "
       "parties.",
       "لا يُعتد بأي تعديل إلا بمحرر كتابيوقعه الطرفان."),

    _r("LG-UNILATERAL-TERM", "high", "exit", "provider",
       "Client may terminate at will; provider has no equivalent right",
       "حق إنهاء منفرد للعميل دون حق مماثل للمقدم",
       [r"terminate\w*\s+.{0,70}(at\s+its\s+(sole\s+)?discretion|for\s+any\s+reason|without\s+cause|for\s+convenience)",
        r"(ينهي|فسخ|انها).{0,70}(ارادته|دون\s+اسباب|بشكل\s+احادي)"],
       "The client can walk away at any time with no kill fee — you may "
       "have already spent weeks unpaid. Demand compensation for work "
       "done plus committed costs.",
       "العميل ينسحب في أي وقت دون تعويض — وقد أنجزت أسابيع بلا أجر. اطلب "
       "أجراً عن المنجز وتكاليف الملتزم بها.",
       "Either party may terminate with [15] days' written notice; upon "
       "termination Client pays for all work performed, committed "
       "third-party costs, and a kill fee of [20]% of the remaining "
       "milestones.",
       "يجوز لأي طرف الإنهاء بإخطار كتابي [15] يوماً؛ وعند الإنهاء يدفع "
       "العميل أجراً عن كل عمل منجز وتكاليف طرف ثالث ملتزم بها وتعويض "
       "إنهاء قدره [20]% من المراحل المتبقية."),
    _r("LG-UNLIMITED-REVISIONS", "medium", "scope", "provider",
       "Unlimited revisions with no defined scope",
       "تعديلات غير محدودة دون نطاق محدد",
       [r"unlimited\s+revision", r"revision\w*\s+.{0,40}(as\s+many|unlimited|number)",
        r"تعديلات.{0,40}(غير\s+محدوده|بلا\s+حد|بلا\s+عدد)"],
       "'Unlimited revisions' with no count or acceptance criteria turns "
       "any project into open-ended free labor.",
       "«تعديلات غير محدودة» بلا عدد أو معايير قبول تحوّل أي مشروع إلى عمل "
       "مجاني مفتوح النهاية.",
       "Provider includes [3] rounds of revisions per deliverable; further "
       "revisions are billed at the hourly rate and scoped in writing.",
       "يشمل المقدم [3] جولات تعديل لكل مخرج؛ وما زاد عنها يُدفع بالساعي "
       "ويُحدّد نطاقه كتابياً."),

    _r("LG-NONCOMPETE", "medium", "scope", "provider",
       "Broad non-compete restricting your other work",
       "منع واسع للمنافسة يقيّد أعمالك الأخرى",
       [r"non-?compete", r"shall\s+not\s+(engage|work|provide\s+services).{0,60}compet",
        r"عدم\s+المنافسه|لا\s+يزاول.{0,40}منافس"],
       "A non-compete covering an entire industry or long period can block "
       "you from earning elsewhere. Time, geography, and scope must be "
       "narrow and paid for.",
       "منع منافسة يشمل قطاعاً كاملاً أو مدة طويلة قد يمنعك من العمل "
       "لغيره. يجب أن يكون ضيق الزمان والمكان والنطاق ومدفوع الثمن.",
       "During the term and for [6] months after, Provider shall not "
       "deliver the same paid service to Client's direct competitors named "
       "in Annex [X]; everything else is unrestricted.",
       "خلال المدة وبعدها [6] أشهر لا يقدّم المقدم الخدمة نفسها لمنافسي "
       "العميل المذكورين في الملحق [X]؛ وما عدا ذلك غير مقيد."),

    _r("LG-EXCLUSIVE", "low", "scope", "provider",
       "Exclusive engagement without a minimum guarantee",
       "تعاقد حصري دون ضمان حد أدنى للأجور",
       [r"(sole\s+and\s+)?exclusive\w*\s+(basis|engagement|services|right|arrangement)",
        r"بالحصريه|حصري\w*\s+لديه"],
       "Exclusivity reserves all your capacity for one client; without a "
       "monthly minimum it is an unpaid option on your calendar.",
       "الحصريه تحجز طاقتك كلها لعميل واحد؛ وبدون حد أدنى شهري هي خيار "
       "غير مدفوع على وقتك.",
       "Provider devotes up to [X] hours/month on an exclusive basis in "
       "exchange for a minimum monthly fee of [amount]; below that fee no "
       "exclusivity applies.",
       "يخصص المقدم حتى [X] ساعة شهرياً بمقابل حصريه مقابل حد أدنى شهري "
       "[مبلغ]؛ ودون هذا الحد الأدنى لا تنطبق الحصريه."),

    _r("LG-PERSONAL-GUARANTEE", "high", "liability", "both",
       "Personal / joint-and-several liability of the owner",
       "ضمان شخصي أو مسؤولية تضامنية لصاحب العمل",
       [r"personally\s+guarantee", r"joint\s+and\s+several\s+liabilit",
        r"ضمان\s+شخصي|مسووليه.{0,25}تضامنيه|كفل.{0,20}شخصيا"],
       "A personal guarantee pierces the limited-liability shield: your "
       "personal assets back the company's debts. Rarely justified for "
       "routine contracts.",
       "الضمان الشخصي يخترق حماية المسؤولية المحدودة: أموالك الشخصية تضمن "
       "ديون الشركة. نادراً ما يُبرَّر في العقود الروتينية.",
       "Liability is limited to the fees paid under this agreement; no "
       "party gives a personal guarantee, and liability is neither joint "
       "nor several.",
       "تُحد المسؤولية بالأجور المدفوعة بموجب هذا العقد؛ ولا يمنح أي طرف "
       "ضماناً شخصياً، ولا تكون المسؤولية تضامنية."),

    _r("LG-UNLIMITED-LIABILITY", "high", "liability", "both",
       "Unlimited liability for one or both parties",
       "مسؤولية غير محدودة لأحد الطرفين أو للطرفين",
       [r"liable\s+(without\s+limit|for\s+any\s+and\s+all|for\s+all\s+losses?)",
        r"unlimited\s+liabilit", r"مسووليه.{0,35}(بلا\s+حد|بلا\s+قيد|غير\s+محدوده|لكل\s+خساره)"],
       "Uncapped liability can exceed everything you ever earned from the "
       "deal. Push for a cap tied to fees paid in the prior 12 months.",
       "المسؤولية بلا سقف قد تتجاوز كل ما كسبته من الصفقة. اطلب سقفاً "
       "مرتبطاً بالأجور المدفوعة في آخر 12 شهراً.",
       "Each party's total liability is capped at the fees paid or payable "
       "in the [12] months preceding the claim; neither party is liable "
       "for indirect or consequential damages.",
       "تُحدّ المسؤولية الإجمالية لكل طرف بالأجور المدفوعة أو المستحقة في "
       "[12] شهراً السابقة للمطالبة؛ ولا يتحمل أي طرف أضراراً غير مباشرة "
       "أو تبعية."),

    _r("LG-ONEWAY-INDEMNITY", "high", "liability", "provider",
       "One-way indemnity running only against the provider",
       "تعويض من طرف واحد في مصلحة العميل فقط",
       [r"indemnif\w+|hold\s+harmless|تعويض|تحميل\s+المسووليه",
        r"(provider|contractor|consultant|supplier|المقدم|المقاول|المستشار|الموريد).{0,90}(indemnif|تعويض|يتحمل|يحمل)|(indemnif|تعويض|يحمل|يتحمل).{0,90}(provider|contractor|supplier|المقدم|المقاول|المستشار|الموريد)"],
       "Indemnity that only flows one way makes you the insurer of the "
       "client's every claim. Make it mutual, fault-based, and capped.",
       "التعويض الأحادي يجعلك مؤميناً لكل مطالبة لدى العميل. اجعله "
       "متبادلاً ومرتبطاً بالخطأ ومحدّداً بسقف.",
       "Each party indemnifies the other only for third-party claims "
       "arising from its own gross negligence or willful misconduct, "
       "subject to the liability cap above.",
       "يعوّض كل طرف الآخر عن مطالبات الأطراف الثالثة فقط الناشئة عن "
       "إهماله الجسيم أو سوء نيته، مع مراعاة سقف المسؤولية أعلاه.",
       mode="all"),

    _r("LG-MORAL-RIGHTS", "medium", "ip", "provider",
       "Blanket waiver of moral rights",
       "تنازل شامل عن الحقوق المعنوية",
       [r"moral\s+rights?\s+(are\s+)?\w*\s*waiv", r"waive\w*\s+.{0,25}moral",
        r"التخلي\s+عن\s+الحقوق\s+المعنويه|الحقوق\s+المعنويه"],
       "A blanket moral-rights waiver can strip attribution and integrity "
       "rights over your creative work — often broader than needed.",
       "التنازل الشامل عن الحقوق المعنوية قد يسقط حقك في النسب وسلامة "
       "العمل الإبداعي — وأكثر من اللازم عادة.",
       "Provider waives moral rights only to the extent necessary for "
       "Client's intended use of the deliverables; attribution remains in "
       "source files unless law forbids it.",
       "يتنازل المقدم عن الحقوق المعنوية بالقدر اللازم فقط لاستخدام العميل "
       "المقصود للمخرجات؛ ويُحفظ النسب في الملفات المصدرية ما لم يمنعه "
       "القانون."),

    _r("LG-DEPOSIT-FULL", "medium", "money", "client",
       "100% payment demanded in advance",
       "اشتراط دفع كامل المبلغ مقدماً",
       [r"100%.{0,30}(advance|upfront|prepay|before|prior)",
        r"(advance|upfront|full\s+payment).{0,40}(before|prior|start)|payment\s+in\s+full\s+.{0,20}(before|prior)",
        r"دفعه\s+مقدمه.{0,40}كامل|كامل\s+المبلغ.{0,40}مقدم|100%\s*(مقدم|مقدما)"],
       "Paying 100% up front leaves the client with zero leverage if "
       "delivery fails. Milestone-based escrow is the fair middle ground.",
       "الدفع الكامل مقدماً يترك العميل بلا أي ضغط تفاوضي إذا فشل التسليم. "
       "الدفع على مراحل هو الوسط العادل.",
       "Payment is split into [3] milestones: [30]% on signing, [40]% on "
       "mid-delivery, [30]% on acceptance; each milestone invoice is due "
       "Net [15] days.",
       "يُقسَّم الدفع إلى [3] مراحل: [30]% عند التوقيع، [40]% عند التسليم "
       "الوسجي، [30]% عند القبول؛ وتُسدَّد فاتورة كل مرحلة خلال [15] يوماً."),

    _r("LG-SETTLE-DISTANT-FORUM", "low", "exit", "both",
       "Distant forum / foreign governing law",
       "اختصاص محكمة بعيدة أو قانون أجنبي",
       [r"governed\s+by\s+the\s+laws?\s+of", r"exclusive\s+jurisdiction",
        r"(تخضع|يخضع).{0,30}قوانين|(اختصاص|تختص).{0,30}محاكم"],
       "Foreign law and a distant exclusive forum raise the real cost of "
       "enforcing any claim — usually hurting the smaller party more.",
       "القانون الأجنبي ومحكمة بعيدة الحصرية ترفع كلفة التنفيذ الحقيقية "
       "لأي مطالبة — وغالباً ما تضر بالطرف الأصغر.",
       "This agreement is governed by the laws of [country]; disputes go "
       "to the courts of [city], or to [free online arbitration] for "
       "amounts under [threshold].",
       "يخضع هذا العقد لقوانين [الدولة]؛ وتختص محاكم [المدينة]، أو "
       "[تحكيم إلكتروني مجاني] للمبالغ دون [الحد]."),

    _r("LG-CONF-INDEFINITE", "low", "data", "both",
       "Confidentiality obligations that never end",
       "التزامات سرية بلا نهاية",
       [r"(indefinite|perpetual|forever|survive).{0,40}confidential",
        r"confidential\w*\s+.{0,30}(indefinite|perpetual)",
        r"سريه.{0,40}(بلا\s+حد|مدي\s+الحياته|ابديه)"],
       "Perpetual confidentiality with no carve-outs can be used to "
       "silence you about facts you already knew. Ask for a fixed term "
       "and standard exclusions.",
       "السرية المطلقة بلا استثناءات قد تُستخدم لإسكاتك عن حقائق عرفتها "
       "سابقاً. اطلب مدة محددة واستثناءات قياسية.",
       "Obligations last [3] years from disclosure and exclude information "
       "already public, independently developed, or required to be "
       "disclosed by law.",
       "يلتزم الطرفان [3] سنوات من تاريخ الإفصاح، وتستثني المعلومات "
       "المنشورة أو المطورة مستقلاً أو المطلوب إفصاحها قانوناً."),
]

RULES_BY_ID = dict((r.id, r) for r in RULES)
SELECTION_ORDER = sorted(RULES, key=lambda r: (-SEVERITY_RANK[r.severity], r.id))


def select_rules(ignore=(), min_severity="info", side=None):
    """Return rules honoring user config: ignore list, severity floor,
    and the user's role in the deal (provider/client/None=both sides)."""
    out = []
    rank = SEVERITY_RANK.get(min_severity, 0)
    for rule in SELECTION_ORDER:
        if rule.id in ignore:
            continue
        if SEVERITY_RANK[rule.severity] < rank:
            continue
        if side and rule.side not in (side, "both"):
            continue
        out.append(rule)
    return out


def get_rule(rule_id):
    return RULES_BY_ID.get(rule_id)

