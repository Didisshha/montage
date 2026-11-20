import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-montage/7dd93770-ed8c-50cb-9cc1-068fa60600fd/scratchpad/scripts")
from montage_gen import Gen, PANT, MAT

W = "/tmp/claude-0/-home-user-montage/7dd93770-ed8c-50cb-9cc1-068fa60600fd/scratchpad/work5/"

# Proofread text of the cut, exactly as spoken (one token = one subtitle screen)
TEXT = """Тестируем ЕГЭшника по не ЕГЭшным вопросам из отборочного МГУшной олимпиады.
Я тебе собрала четыре вопроса, с которыми олимпиадники справились хуже всего.
Твоя задача — хотя бы вот из этих четырёх ответить на один.
Какой спектакль смотрел Червяков в «Смерти чиновника», когда чихнул на генерала Бризжалова?
Жёстко, да? Жёстко, очень.
Но, короче, это «Корневильские колокола».
А статью я скину в свой телеграм-канал «Пантеон литература».
А кто предложил Горькому название «На дне»?
«На дне»… это Станиславский?
Нет, прикинь.
Но это Леонид Андреев, короче говоря.
Его дружок.
Ещё один вопрос. Кому Тургенев посвятил «Отцов и детей», в память какого человека?
Это же Виссарион Григорьевич Белинский.
Это в эпиграфе написано, друзья.
Кстати, а у Фариши, опять же, забирайте в телеграм-канале файл с анализом всех эпиграфов ЕГЭшных произведений.
Ставь себе жирную галочку.
И последний вопрос. К чьей поэме — нужна фамилия автора — отсылает название рассказа Толстого «Кавказский пленник»?
Пушкин.
Ну, ну всё. Я тебе рядышком поставлю галочку, просто потому что ты умница.
Короче говоря, как вы понимаете, на ЕГЭ что-то прям зубрить не нужно, но надо знать чётко очерченный материал.
Поэтому вперёд в закреп, «Мать стобалльников» вас ждёт.
Если вы готовитесь к олимпиаде, вам нужно знать гораздо шире и больший материал.
У меня в закрепе вы можете забрать абсолютно всё, что вам потребуется."""

g = Gen(W + "cut2.segments.json", W + "cut2_words.json", W + "faces2.json", TEXT, {"L": (300, 790), "R": (825, 710)})
g.highlight = ["ЕГЭшника", "МГУшной", "«Корневильские", "колокола»", "Андреев", "Леонид", "Белинский", "Пушкин",
               "эпиграфов", "«Пантеон", "стобалльников»", "«Мать"]
w = g.wt
T = dict(q1=w("Какой"), otvet1=w("«Корневильские"), cta1=w("статью"), q2=w("кто", w("литература»")) - 0.25,
         stan=w("Станиславский"), net=w("Нет", w("Станиславский")), andr=w("Андреев"), druzh=w("дружок"),
         q3=w("Ещё"), bel=w("Белинский"), epig=w("эпиграфе"), cta2=w("Кстати"), galka=w("Ставь"),
         q4=w("последний") - 0.2, plen=w("пленник»"), push=w("Пушкин"), nuvse=w("всё", w("Пушкин")), umn=w("умница"),
         outro=w("Короче", w("умница")), zakrep1=w("закреп", w("умница")), olymp=w("Если", w("ждёт")), zakrep2=w("закрепе"))
print({k: round(v, 2) for k, v in T.items()})

windows = [(T["cta1"], T["q2"] - 0.05, "R"), (T["cta2"], T["galka"] - 0.1, "R"),
           (T["zakrep1"] - 1.2, T["olymp"] - 0.1, "L"), (T["zakrep2"] - 0.8, g.END, "R")]
g.build_framing(windows)

# hook
g.texts.append({"t": 0.05, "out": w("МГУшной") - 0.05, "x": 540, "y": 1060,
                "lines": [["ТЕСТ", "UB", 120, "white"], ["для ЕГЭшника", "UB", 66, "cream"]], "anim": "pop", "d_in": 0.14})
g.stamp(w("МГУшной"), w("собрала") - 0.1, "ОТБОР МГУ", color="lav", size=72, y=1080, sfx=None)
g.card(w("четыре"), w("задача"), None, icon="bigtext", text="4", size=0.42, caption="вопроса")
# questions
g.header(1, "вопрос", "Чехов", T["q1"], T["cta1"] - 0.1)
g.header(2, "вопрос", "Горький", T["q2"], T["q3"] - 0.1)
g.header(3, "вопрос", "Тургенев", T["q3"], T["cta2"] - 0.1)
g.header(4, "вопрос", "Толстой", T["q4"], T["umn"] + 0.5)
g.card(w("«Смерти"), w("Бризжалова?", end=True) + 0.6, "R", icon="bigtext", text="«Смерть\nчиновника»", size=0.15, caption="Чехов")
g.card(w("Жёстко"), T["otvet1"] - 0.1, "L", icon="warning", caption="жёстко")
g.stamp(T["otvet1"], T["cta1"] - 0.1, "«КОРНЕВИЛЬСКИЕ КОЛОКОЛА»", size=40, sfx="ding", gain=-10)
g.card(w("«На", T["q2"]) - 0.1, T["stan"] - 0.1, "R", icon="bigtext", text="«На дне»", size=0.2, caption="Горький")
g.stamp(T["stan"] + 0.3, T["net"] + 0.7, "МИМО", color="red", size=80, sfx="buzzer", gain=-12)
g.stamp(T["andr"] - 0.3, T["druzh"] + 0.8, "ЛЕОНИД АНДРЕЕВ", size=54, sfx="ding", gain=-10)
g.card(w("Тургенев"), T["bel"] - 0.15, "R", icon="bigtext", text="«Отцы\nи дети»", size=0.18, caption="Тургенев")
g.stamp(T["bel"], T["epig"] - 0.1, "ВЕРНО!", color="green", size=84, sfx="correct", gain=-10)
g.card(T["epig"], T["cta2"] - 0.1, "R", icon="quote", caption="эпиграф")
g.stamp(T["galka"], T["q4"] - 0.1, "+1 ГАЛОЧКА", color="green", size=64)
g.card(w("Толстого"), T["push"] - 0.1, "R", icon="bigtext", text="«Кавказский\nпленник»", size=0.13, caption="Толстой")
g.stamp(T["push"], T["umn"] - 0.6, "ПУШКИН — ВЕРНО!", color="green", size=56, sfx="correct", gain=-10)
g.stamp(T["umn"] - 0.5, T["outro"] - 0.05, "2 ИЗ 4", size=80, sfx="achievement", gain=-12)
g.sparkles += [{"t": T["push"], "out": T["outro"] - 0.1, "side": "L", "y": 470},
               {"t": T["push"] + 0.1, "out": T["outro"] - 0.1, "side": "R", "y": 470}]
g.shakes = [T["stan"] + 0.3, T["bel"], T["push"]]

# Telegram screens (no sounds on screens)
a, b, _ = windows[0]; m = a + (b - a) * 0.5
g.screen(a, m, PANT + "IMG_3190.png", y=1080, type={"box": [0.115, 0.15, 0.48, 0.31], "start": 0.15, "dur": 0.7}, taps=[[m - a - 0.35, 0.45, 0.79]])
g.screen(m, b + 0.05, PANT + "IMG_3191.png", y=1190, anim="pop", taps=[[0.35, 0.45, 0.125]])
g.label(a + 0.3, b - 0.1, "тгк: пантеон литература")
a, b, _ = windows[1]; d = (b - a) / 4
g.screen(a, a + d, MAT + "IMG_3195.png", y=1080, type={"box": [0.115, 0.13, 0.50, 0.33], "start": 0.15, "dur": 0.7}, taps=[[d - 0.3, 0.5, 0.77]])
g.screen(a + d, a + 2 * d, MAT + "IMG_3199.png", y=1150, anim="pop")
g.screen(a + 2 * d, a + 3 * d, MAT + "IMG_3196.png", y=1190, anim="pop", taps=[[0.35, 0.42, 0.115]])
g.screen(a + 3 * d, b + 0.05, MAT + "IMG_3197.png", y=1190, anim="pop", taps=[[0.5, 0.40, 0.42]])
g.label(a + 0.3, a + 2 * d, "тгк: Мать стобалльников", color="lav")
g.label(a + 2 * d + 0.1, b - 0.1, "анализ всех эпиграфов")
a, b, _ = windows[2]; m = a + (b - a) * 0.45
g.screen(a, m, MAT + "IMG_3199.png", x=790, y=1150)
g.screen(m, b + 0.05, MAT + "IMG_3196.png", x=790, y=1190, anim="pop", taps=[[0.4, 0.42, 0.115]])
g.label(a + 0.3, b - 0.1, "закреп: Мать стобалльников", who="L", color="lav")
a, b, _ = windows[3]; m = a + (b - a) * 0.4
g.screen(a, m, PANT + "IMG_3191.png", y=1190, taps=[[0.4, 0.45, 0.125]])
g.screen(m, b + 0.3, PANT + "IMG_3193.png", y=1190, anim="pop", taps=[[0.6, 0.40, 0.31]])
g.label(a + 0.3, b, "закреп: пантеон литература")

g.write(W + "plan_final.json", flashes=[h["t"] for h in g.headers])
