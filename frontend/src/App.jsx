import { useEffect, useMemo, useState } from "react";

const pages = [
  ["map", "Карта"],
  ["goals", "Цели"],
  ["week", "Неделя"],
  ["habits", "Привычки"],
  ["reflect", "Рефлексия"],
  ["chat", "Агент"],
  ["settings", "Настройки"],
];

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function App() {
  const [page, setPage] = useState("map");
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("navCollapsed") === "1");
  const [me, setMe] = useState(null);
  const [areas, setAreas] = useState([]);
  const [goals, setGoals] = useState([]);
  const [habits, setHabits] = useState([]);
  const [week, setWeek] = useState(null);
  const [reflections, setReflections] = useState([]);
  const [error, setError] = useState("");

  async function reload() {
    try {
      const [m, a, g, h, w, r] = await Promise.all([
        api("/api/me"),
        api("/api/areas"),
        api("/api/goals"),
        api("/api/habits"),
        api("/api/week"),
        api("/api/reflections"),
      ]);
      setMe(m);
      setAreas(a);
      setGoals(g);
      setHabits(h);
      setWeek(w);
      setReflections(r);
      setError("");
    } catch (e) {
      setError(String(e.message || e));
    }
  }

  useEffect(() => {
    reload();
  }, []);

  function toggleNav() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("navCollapsed", next ? "1" : "0");
  }

  return (
    <div className={`layout ${collapsed ? "collapsed" : ""}`}>
      <nav>
        <button className="toggle" type="button" onClick={toggleNav} title={collapsed ? "Развернуть" : "Свернуть"}>
          {collapsed ? "›" : "‹"}
        </button>
        <h1>Агент развития</h1>
        <div className="nav-links">
          {pages.map(([id, label]) => (
            <button key={id} className={`nav-item ${page === id ? "active" : ""}`} onClick={() => setPage(id)}>
              {label}
            </button>
          ))}
        </div>
        {me && !me.google_connected && <p className="gstatus">Google не подключён</p>}
      </nav>
      <main>
        {error && <p className="warn">{error}</p>}
        {page === "map" && <MapPage areas={areas} goals={goals} onReload={reload} />}
        {page === "goals" && <GoalsPage goals={goals} areas={areas} onReload={reload} />}
        {page === "week" && <WeekPage week={week} onReload={reload} />}
        {page === "habits" && <HabitsPage habits={habits} onReload={reload} />}
        {page === "reflect" && <ReflectPage reflections={reflections} onReload={reload} />}
        {page === "chat" && <ChatPage />}
        {page === "settings" && <SettingsPage me={me} onReload={reload} />}
      </main>
    </div>
  );
}

function MapPage({ areas, goals, onReload }) {
  const [name, setName] = useState("");
  return (
    <div>
      <h2>Карта сфер</h2>
      <div className="cards">
        {areas.map((a) => (
          <div className="card" key={a.id} style={{ borderTop: `4px solid ${a.color}` }}>
            <h3>{a.name}</h3>
            <p className="muted">{a.description || "—"}</p>
            <p>
              Целей: {goals.filter((g) => g.area_id === a.id).length}
            </p>
          </div>
        ))}
      </div>
      <div className="row" style={{ marginTop: 16 }}>
        <input placeholder="Своя сфера" value={name} onChange={(e) => setName(e.target.value)} />
        <button
          className="btn"
          onClick={async () => {
            if (!name.trim()) return;
            await api("/api/areas", { method: "POST", body: JSON.stringify({ name }) });
            setName("");
            onReload();
          }}
        >
          Добавить
        </button>
      </div>
    </div>
  );
}

function GoalsPage({ goals, areas, onReload }) {
  const [form, setForm] = useState({ title: "", deadline: "", area_id: "", specific: "", measurable: "" });
  const [open, setOpen] = useState(null);
  return (
    <div>
      <h2>SMART-цели</h2>
      <div className="card">
        <div className="row">
          <input placeholder="Цель" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
          <select value={form.area_id} onChange={(e) => setForm({ ...form, area_id: e.target.value })}>
            <option value="">Сфера</option>
            {areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </div>
        <textarea
          style={{ width: "100%", marginTop: 8 }}
          placeholder="Specific / Measurable"
          value={form.specific}
          onChange={(e) => setForm({ ...form, specific: e.target.value })}
        />
        <button
          className="btn"
          style={{ marginTop: 8 }}
          onClick={async () => {
            await api("/api/goals", {
              method: "POST",
              body: JSON.stringify({
                ...form,
                area_id: form.area_id ? Number(form.area_id) : null,
              }),
            });
            setForm({ title: "", deadline: "", area_id: "", specific: "", measurable: "" });
            onReload();
          }}
        >
          Сохранить цель
        </button>
      </div>
      {goals.map((g) => (
        <div className="card" key={g.id} style={{ marginTop: 12 }}>
          <h3>{g.title}</h3>
          <p className="muted">до {g.deadline}</p>
          {g.stages.map((s) => (
            <div className="stage" key={s.id}>
              <b>{s.title}</b> {s.preserved ? "(сохранено)" : ""} — {s.status}
              <div className="muted">{s.brief}</div>
              {s.tasks.map((t) => (
                <label key={t.id} style={{ display: "block" }}>
                  <input
                    type="checkbox"
                    checked={t.status === "done"}
                    onChange={() =>
                      api(`/api/tasks/${t.id}?status=${t.status === "done" ? "todo" : "done"}`, {
                        method: "PATCH",
                      }).then(onReload)
                    }
                  />{" "}
                  {t.title}
                </label>
              ))}
              <button className="btn ghost" onClick={() => api(`/api/stages/${s.id}?status=done`, { method: "PATCH" }).then(onReload)}>
                Этап закрыт
              </button>
            </div>
          ))}
          <button className="btn" onClick={() => setOpen(g.id)}>
            Добавить этап
          </button>
          {open === g.id && <StageForm goalId={g.id} onDone={onReload} />}
        </div>
      ))}
    </div>
  );
}

function StageForm({ goalId, onDone }) {
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [deadline, setDeadline] = useState("");
  return (
    <div className="row" style={{ marginTop: 8 }}>
      <input placeholder="Этап" value={title} onChange={(e) => setTitle(e.target.value)} />
      <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
      <input placeholder="ТЗ" value={brief} onChange={(e) => setBrief(e.target.value)} />
      <button
        className="btn"
        onClick={async () => {
          await api(`/api/goals/${goalId}/stages`, {
            method: "POST",
            body: JSON.stringify({ title, brief, deadline: deadline || null }),
          });
          onDone();
        }}
      >
        OK
      </button>
    </div>
  );
}

function WeekGrid({ events }) {
  const labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
  const startHour = 7;
  const endHour = 23;
  const hourH = 48;
  const monday = new Date();
  monday.setHours(0, 0, 0, 0);
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
  const today = new Date();
  const items = (events || [])
    .map((e) => {
      if (!e.start || !String(e.start).includes("T")) return null;
      const s = new Date(e.start);
      const en = new Date(e.end || e.start);
      if (Number.isNaN(s.getTime())) return null;
      return { title: e.title || "Без названия", s, en: Number.isNaN(en.getTime()) ? s : en };
    })
    .filter(Boolean);
  const hours = [];
  for (let h = startHour; h < endHour; h += 1) hours.push(String(h).padStart(2, "0") + ":00");
  const days = labels.map((label, i) => {
    const day = new Date(monday);
    day.setDate(monday.getDate() + i);
    const mine = items
      .filter((ev) => ev.s.toDateString() === day.toDateString())
      .sort((a, b) => a.s - b.s);
    const laneEnds = [];
    mine.forEach((ev) => {
      let lane = laneEnds.findIndex((end) => end <= ev.s.getTime());
      if (lane < 0) {
        lane = laneEnds.length;
        laneEnds.push(ev.en.getTime());
      } else laneEnds[lane] = ev.en.getTime();
      ev.lane = lane;
    });
    const lanes = Math.max(1, laneEnds.length);
    return { label, day, mine, lanes, today: day.toDateString() === today.toDateString() };
  });
  const fmt = (d) => d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  return (
    <div className="gcal">
      <div className="hours">
        {hours.map((h) => (
          <div className="hour" key={h}>{h}</div>
        ))}
      </div>
      <div className="days">
        {days.map((col) => (
          <div className="day" key={col.label}>
            <div className={`dayhead${col.today ? " today" : ""}`}>{col.label} {col.day.getDate()}</div>
            <div className="daybody" style={{ height: (endHour - startHour) * hourH }}>
              {col.mine.map((ev, idx) => {
                const sh = ev.s.getHours() + ev.s.getMinutes() / 60;
                const eh = Math.max(sh + 0.4, ev.en.getHours() + ev.en.getMinutes() / 60);
                const top = Math.max(0, (sh - startHour) * hourH);
                const height = Math.max(22, Math.min((endHour - startHour) * hourH - top, (eh - sh) * hourH));
                const width = 100 / col.lanes;
                return (
                  <div
                    className="ev"
                    key={idx}
                    style={{ top, height, left: `${ev.lane * width}%`, width: `calc(${width}% - 4px)` }}
                  >
                    <b>{ev.title}</b>
                    <span>{fmt(ev.s)}–{fmt(ev.en)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function WeekPage({ week, onReload }) {
  if (!week) return <p>Загрузка…</p>;
  return (
    <div>
      <h2>Неделя</h2>
      <p>
        Событий: {week.facts.event_count}, часов: {week.facts.hours_logged}, задач закрыто:{" "}
        {week.facts.tasks_done.length}
      </p>
      <button className="btn" onClick={() => api("/api/review/generate", { method: "POST" }).then(onReload)}>
        Собрать обзор недели
      </button>
      <h3>Календарь</h3>
      <WeekGrid events={week.events || []} />
      <h3>Черновики</h3>
      {week.pending.map((p) => (
        <div key={p.id} className="card">
          {p.preview}
          {p.payload?.conflicts?.length ? <p className="warn">Конфликт</p> : null}
          <div className="row">
            <button className="btn" onClick={() => api(`/api/pending/${p.id}/approve`, { method: "POST" }).then(onReload)}>
              Подтвердить
            </button>
            <button className="btn ghost" onClick={() => api(`/api/pending/${p.id}/reject`, { method: "POST" }).then(onReload)}>
              Отклонить
            </button>
          </div>
        </div>
      ))}
      {week.reviews.map((r) => (
        <div className="card" key={r.id}>
          <h3>Обзор {r.week_start}</h3>
          <pre style={{ whiteSpace: "pre-wrap" }}>{r.content}</pre>
          <p className="muted">{r.pace_notes}</p>
        </div>
      ))}
    </div>
  );
}

function HabitsPage({ habits, onReload }) {
  const [title, setTitle] = useState("");
  const today = new Date().toISOString().slice(0, 10);
  return (
    <div>
      <h2>Привычки</h2>
      {habits.map((h) => (
        <label key={h.id} className="card" style={{ display: "block", marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={h.today_done}
            onChange={() =>
              api(`/api/habits/${h.id}/log`, {
                method: "POST",
                body: JSON.stringify({ day: today, done: !h.today_done }),
              }).then(onReload)
            }
          />{" "}
          {h.title} <span className="muted">{h.cadence}</span>
        </label>
      ))}
      <div className="row">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Новая привычка" />
        <button
          className="btn"
          onClick={async () => {
            await api("/api/habits", { method: "POST", body: JSON.stringify({ title }) });
            setTitle("");
            onReload();
          }}
        >
          Добавить
        </button>
      </div>
    </div>
  );
}

function ReflectPage({ reflections, onReload }) {
  const monday = useMemo(() => {
    const d = new Date();
    const day = (d.getDay() + 6) % 7;
    d.setDate(d.getDate() - day);
    return d.toISOString().slice(0, 10);
  }, []);
  const [energy, setEnergy] = useState(7);
  const [prod, setProd] = useState(7);
  const [text, setText] = useState("");
  return (
    <div>
      <h2>Рефлексия</h2>
      <div className="card">
        <p>Энергия {energy}/10</p>
        <input type="range" min="1" max="10" value={energy} onChange={(e) => setEnergy(Number(e.target.value))} />
        <p>Продуктивность {prod}/10</p>
        <input type="range" min="1" max="10" value={prod} onChange={(e) => setProd(Number(e.target.value))} />
        <textarea style={{ width: "100%" }} value={text} onChange={(e) => setText(e.target.value)} />
        <button
          className="btn"
          onClick={() =>
            api("/api/reflections", {
              method: "POST",
              body: JSON.stringify({ week_start: monday, energy, productivity: prod, text }),
            }).then(onReload)
          }
        >
          Сохранить
        </button>
      </div>
      {reflections.map((r) => (
        <div className="card" key={r.id}>
          <b>
            {r.week_start}: {r.energy}/{r.productivity}
          </b>
          <p>{r.text}</p>
        </div>
      ))}
    </div>
  );
}

function ChatPage() {
  const [text, setText] = useState("");
  const [msgs, setMsgs] = useState([]);
  const [busy, setBusy] = useState(false);
  async function send() {
    if (!text.trim() || busy) return;
    const mine = text;
    setText("");
    setMsgs((m) => [...m, { role: "me", content: mine }]);
    setBusy(true);
    try {
      const res = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: mine }) });
      setMsgs((m) => [...m, { role: "bot", content: res.reply }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "bot", content: String(e.message || e) }]);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="chat">
      <div className="msgs">
        {msgs.map((m, i) => (
          <div key={i} className={`bubble ${m.role === "me" ? "me" : ""}`}>
            {m.content}
          </div>
        ))}
      </div>
      <div className="row">
        <input
          style={{ flex: 1 }}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Напиши агенту"
        />
        <button className="btn" onClick={send} disabled={busy}>
          {busy ? "…" : "Отправить"}
        </button>
      </div>
    </div>
  );
}

function SettingsPage({ me, onReload }) {
  const [form, setForm] = useState(me || {});
  useEffect(() => setForm(me || {}), [me]);
  if (!me) return null;
  return (
    <div>
      <h2>Настройки</h2>
      <div className="card grid">
        <label>
          Часовой пояс
          <input value={form.timezone || ""} onChange={(e) => setForm({ ...form, timezone: e.target.value })} />
        </label>
        <div className="row">
          <input value={form.work_start || ""} onChange={(e) => setForm({ ...form, work_start: e.target.value })} />
          <input value={form.work_end || ""} onChange={(e) => setForm({ ...form, work_end: e.target.value })} />
        </div>
        <input
          value={form.work_days || ""}
          onChange={(e) => setForm({ ...form, work_days: e.target.value })}
          placeholder="Рабочие дни 1,2,3,4,5"
        />
        <div className="row">
          <select
            value={form.reflection_weekday ?? ""}
            onChange={(e) => setForm({ ...form, reflection_weekday: e.target.value ? Number(e.target.value) : null })}
          >
            <option value="">Рефлексия: день</option>
            {["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"].map((d, i) => (
              <option key={d} value={i + 1}>
                {d}
              </option>
            ))}
          </select>
          <input
            type="time"
            value={form.reflection_time || ""}
            onChange={(e) => setForm({ ...form, reflection_time: e.target.value })}
          />
        </div>
        <button className="btn" onClick={() => api("/api/me", { method: "PUT", body: JSON.stringify(form) }).then(onReload)}>
          Сохранить
        </button>
        <button className="btn ghost" onClick={() => api("/api/google/connect", { method: "POST" }).then(onReload)}>
          Подключить Google Calendar
        </button>
      </div>
    </div>
  );
}
