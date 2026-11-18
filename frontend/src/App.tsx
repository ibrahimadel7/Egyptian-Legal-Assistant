import { useEffect, useRef, useState } from "react";
import type { ReactNode, Dispatch, SetStateAction } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import logoAsset from "./assets/logo.svg";
import {
  ArrowLeft,
  BookOpen,
  Check,
  Copy,
  Info,
  Menu,
  MessageCircle,
  Plus,
  Scale,
  Send,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  X,
  Bookmark,
  Settings,
  Lightbulb,
} from "lucide-react";
import type { Conversation, Message, Source } from "./types";
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(
  /\/$/,
  "",
);
const PRODUCT_NAME = "قانوني";
const PRODUCT_NAME_EN = "Qanouny";
type ApiSource = {
  source_id: string;
  law_name: string;
  categories: string;
  unit_label: string;
  unit_type: string;
  article_number: string;
  excerpt: string;
  expanded: boolean;
};
type ApiResponse = {
  conversation_id: string;
  status: "answered" | "needs_clarification";
  answer: string;
  sources: ApiSource[];
};
type ApiHistoryMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources?: ApiSource[];
};
type ApiConversationSummary = {
  id: string;
  title: string;
  updated_at: string;
};
function mapSource(source: ApiSource): Source {
  return {
    id: source.source_id,
    title: source.law_name || "اسم التشريع غير متاح في البيانات",
    law: source.categories || source.unit_type || "بيانات التصنيف غير متاحة",
    article:
      source.article_number || source.unit_label || "رقم المادة غير متاح",
    excerpt: source.excerpt,
    status: source.expanded
      ? "مقطع سياقي مجاور للمقطع المسترجع"
      : "مقطع مسترجع من قاعدة البيانات — لم يتم التحقق من حداثة التشريع",
  };
}
const courtImage = "/court.jpg";
function Logo({ small = false }: { small?: boolean }) {
  return (
    <img
      className={small ? "logo logo-small" : "logo"}
      src={logoAsset}
      alt={`شعار ${PRODUCT_NAME}`}
    />
  );
}
function Button({
  children,
  onClick,
  secondary = false,
}: {
  children: ReactNode;
  onClick: () => void;
  secondary?: boolean;
}) {
  return (
    <button
      className={secondary ? "btn btn-secondary" : "btn"}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
function Landing({ goChat }: { goChat: () => void }) {
  const [mobileNav, setMobileNav] = useState(false);
  return (
    <div className="landing" dir="rtl">
      <header className="nav wrap">
        <a href="#top" className="brand">
          <Logo />
          <span>{PRODUCT_NAME} <small className="brand-en">{PRODUCT_NAME_EN}</small></span>
        </a>
        <nav className={mobileNav ? "nav-open" : ""}>
          <a href="#top" onClick={() => setMobileNav(false)}>
            الرئيسية
          </a>
          <a href="#features" onClick={() => setMobileNav(false)}>
            المميزات
          </a>
          <a href="#how" onClick={() => setMobileNav(false)}>
            كيف يعمل
          </a>
          <a href="#about" onClick={() => setMobileNav(false)}>
            عن المنتج
          </a>
        </nav>
        <button
          className="mobile-nav-toggle icon-btn"
          onClick={() => setMobileNav((v) => !v)}
          aria-label="قائمة التنقل"
        >
          <Menu />
        </button>
        <button className="btn nav-cta" onClick={goChat}>
          ابدأ الآن <ArrowLeft size={16} />
        </button>
      </header>
      <main id="top">
        <section className="hero wrap">
          <div className="hero-copy">
            <span className="eyebrow">وضوح قانوني، بخطوات أبسط</span>
            <h1>
              مساعدك القانوني
              <br />
              <em>لفهم القوانين المصرية</em>
            </h1>
            <p>
              اسأل عن القوانين واللوائح المصرية، واحصل على إجابات واضحة تساعدك
              على فهم النصوص والوصول إلى المصادر القانونية ذات الصلة.
            </p>
            <div className="hero-actions">
              <Button onClick={goChat}>
                ابدأ المحادثة <ArrowLeft size={17} />
              </Button>
              <a className="text-link" href="#features">
                تعرف على المنتج <ArrowLeft size={15} />
              </a>
            </div>
            <div className="trust-line">
              <ShieldCheck size={17} /> مصادر قابلة للفحص، لا إجابات بلا سند
            </div>
          </div>
          <div className="hero-visual">
            <img
              src={courtImage}
              alt="مبنى دار القضاء العالي في وسط القاهرة"
              width={800}
              height={450}
              loading="eager"
              decoding="async"
              fetchPriority="high"
            />
            <div className="image-caption">
              <span>دار القضاء العالي</span>
              <small>القاهرة، مصر</small>
            </div>
          </div>
        </section>
        <section className="features wrap" id="features">
          <div className="section-intro">
            <span className="eyebrow">ما الذي يقدمه؟</span>
            <h2>المعلومة القانونية تبدأ من مصدرها</h2>
          </div>
          <div className="feature-grid">
            <article className="feature">
              <span className="feature-icon">
                <BookOpen />
              </span>
              <h3>مصادر قانونية موثوقة</h3>
              <p>
                الهدف هو ربط الإجابات بالنصوص القانونية ذات الصلة وإتاحة
                مراجعتها.
              </p>
            </article>
            <article className="feature">
              <span className="feature-icon">
                <Lightbulb />
              </span>
              <h3>شرح واضح ومبسط</h3>
              <p>
                تبسيط اللغة القانونية مع الحفاظ على المعنى والتمييز بين النص
                وشرحه.
              </p>
            </article>
            <article className="feature">
              <span className="feature-icon">
                <Scale />
              </span>
              <h3>شفافية المصادر</h3>
              <p>
                اعرف ما الذي يستند إليه الشرح، وافحص المرجع قبل الاعتماد عليه.
              </p>
            </article>
          </div>
        </section>
        <section className="how wrap" id="how">
          <div>
            <span className="eyebrow">طريقة الاستخدام</span>
            <h2>اسأل. افهم. راجع المصدر.</h2>
          </div>
          <p>
            اكتب سؤالك بلغتك، واستكشف المعلومات ذات الصلة. ستُصمم التجربة لإظهار
            النصوص المرجعية وحدود ما يمكن استنتاجه منها بوضوح.
          </p>
        </section>
        <section className="legal-notice wrap" id="about">
          <Info size={19} />
          <p>
            للمعلومات والمساعدة القانونية فقط، ولا يُعد بديلاً عن استشارة محامٍ
            مختص.
          </p>
        </section>
      </main>
      <footer className="footer wrap">
        <span>{PRODUCT_NAME} — {PRODUCT_NAME_EN}</span>
        <span>مشروع معلوماتي مستقل — ليس جهة حكومية</span>
      </footer>
      <div className="photo-credit">
        الصورة: Bastique / Wikimedia Commons · CC BY 3.0
      </div>
    </div>
  );
}
function Sidebar({
  items,
  active,
  onNew,
  onSelect,
  open,
  onClose,
  onInfo,
}: {
  items: Conversation[];
  active: string | null;
  onNew: () => void;
  onSelect: (id: string) => void;
  open: boolean;
  onClose: () => void;
  onInfo: () => void;
}) {
  return (
    <>
      <div
        className={open ? "drawer-backdrop show" : "drawer-backdrop"}
        onClick={onClose}
      />
      <aside className={open ? "sidebar sidebar-open" : "sidebar"}>
        <div className="side-brand">
          <Logo />
          <span>{PRODUCT_NAME} <small className="brand-en">{PRODUCT_NAME_EN}</small></span>
          <button
            className="icon-btn close-drawer"
            onClick={onClose}
            aria-label="إغلاق القائمة"
          >
            <X />
          </button>
        </div>
        <button className="new-chat" onClick={onNew}>
          <Plus size={17} /> محادثة جديدة
        </button>
        <div className="side-label">المحادثات الأخيرة</div>
        <div className="conversation-list">
          {items.map((c) => (
            <button
              key={c.id}
              className={
                active === c.id ? "conversation active" : "conversation"
              }
              onClick={() => {
                onSelect(c.id);
                onClose();
              }}
            >
              <MessageCircle size={16} />
              <span>{c.title}</span>
              {c.saved && <Bookmark size={13} className="saved-icon" />}
            </button>
          ))}
        </div>
        <div className="side-bottom">
          <button className="side-action" onClick={onInfo}>
            <Settings size={16} /> الإعدادات
          </button>
          <button className="side-action" onClick={onInfo}>
            <Info size={16} /> عن المنتج
          </button>
          <div className="side-disclaimer">
            نسخة تجريبية للواجهة
            <br />
            لا تقدم استشارات قانونية فعلية
          </div>
        </div>
      </aside>
    </>
  );
}
function SourceCard({
  source,
}: {
  source: NonNullable<Message["sources"]>[number];
}) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(
        `${source.title}\n${source.law}\n${source.article}\n${source.excerpt}`,
      );
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  };
  return (
    <article className="source-card">
      <div className="source-top">
        <span className="source-label">
          <BookOpen size={15} /> المصدر القانوني
        </span>
        <div className="source-actions">
          <button onClick={copy} aria-label="نسخ المصدر">
            {copied ? <Check size={13} /> : <Copy size={13} />}
            <span>{copied ? "تم النسخ" : "نسخ المصدر"}</span>
          </button>
        </div>
      </div>
      <h4>{source.title}</h4>
      <div className="source-meta">
        <span>{source.law}</span>
        <span>{source.article}</span>
      </div>
      <blockquote>{source.excerpt}</blockquote>
      <div className="source-status">
        <Info size={13} />
        {source.status}
      </div>
    </article>
  );
}
function ChatMessage({
  message,
  onFeedback,
}: {
  message: Message;
  onFeedback: (v: "up" | "down") => void;
}) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div
      className={
        message.role === "user"
          ? "message-row user-row"
          : "message-row assistant-row"
      }
    >
      {message.role === "assistant" && (
        <div className="assistant-mark">
          <Logo small />
        </div>
      )}
      <div className={message.role === "user" ? "user-bubble" : "answer-wrap"}>
        <div className="message-content">
          {message.role === "assistant" && (
            <div className="answer-kicker">إجابة توضيحية</div>
          )}
          {message.role === "assistant" ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          ) : (
            <p>{message.content}</p>
          )}
        </div>
        {message.sources?.map((s) => (
          <SourceCard key={s.id} source={s} />
        ))}
        {message.role === "assistant" && (
          <div className="message-tools">
            <button onClick={copy} aria-label="نسخ الإجابة">
              {copied ? <Check size={15} /> : <Copy size={15} />}
              <span>{copied ? "تم النسخ" : "نسخ"}</span>
            </button>
            <span className="tool-divider" />
            <button
              className={message.feedback === "up" ? "chosen" : ""}
              onClick={() => onFeedback("up")}
              aria-label="إجابة مفيدة"
            >
              <ThumbsUp size={15} />
            </button>
            <button
              className={message.feedback === "down" ? "chosen" : ""}
              onClick={() => onFeedback("down")}
              aria-label="إجابة غير مفيدة"
            >
              <ThumbsDown size={15} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
const suggestions = [
  "ما هي شروط عقد الإيجار؟",
  "ما هي حقوق العامل في الإجازات؟",
  "ما الفرق بين الجنحة والجناية؟",
];
function Chat({
  conversations,
  setConversations,
  active,
  setActive,
}: {
  conversations: Conversation[];
  setConversations: Dispatch<SetStateAction<Conversation[]>>;
  active: string | null;
  setActive: (id: string | null) => void;
}) {
  const [draft, setDraft] = useState("");
  const [drawer, setDrawer] = useState(false);
  const [help, setHelp] = useState(false);
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const current = conversations.find((c) => c.id === active);
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/conversations`)
      .then((response) => {
        if (!response.ok) throw new Error("تعذر تحميل المحادثات المحفوظة.");
        return response.json() as Promise<ApiConversationSummary[]>;
      })
      .then((items) => {
        if (cancelled || !Array.isArray(items)) return;
        setConversations(
          items.map((item) => ({
            id: item.id,
            title: item.title,
            messages: [],
          })),
        );
      })
      .catch(() => {
        if (!cancelled) setConversations([]);
      });
    return () => {
      cancelled = true;
    };
  }, [setConversations]);
  useEffect(() => {
    scrollRef.current?.scrollTo?.({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [current?.messages.length, sending]);
  const newChat = () => {
    setActive(null);
    setDraft("");
    setDrawer(false);
  };
  const selectConversation = async (id: string) => {
    const existing = conversations.find((conversation) => conversation.id === id);
    if (existing?.messages.length) {
      setActive(id);
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/conversations/${id}`);
      if (!response.ok) throw new Error("تعذر تحميل المحادثة.");
      const data = (await response.json()) as {
        conversation_id: string;
        messages: ApiHistoryMessage[];
      };
      const messages: Message[] = data.messages.map((message) => ({
        id: String(message.id),
        role: message.role,
        content: message.content,
        sources: message.sources?.map(mapSource),
      }));
      setConversations((prev) =>
        prev.map((conversation) =>
          conversation.id === id ? { ...conversation, messages } : conversation,
        ),
      );
      setActive(id);
    } catch (error) {
      const detail =
        error instanceof Error ? error.message : "تعذر تحميل المحادثة.";
      setHelp(true);
      console.error(detail);
    }
  };
  const submit = async (value = draft) => {
    const text = value.trim();
    if (!text || sending) return;
    const user: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text,
    };
    const localId = active || `pending-${Date.now()}`;
    setConversations((prev) => {
      const found = prev.find((c) => c.id === localId);
      if (found)
        return prev.map((c) =>
          c.id === localId ? { ...c, messages: [...c.messages, user] } : c,
        );
      return [
        { id: localId, title: text.slice(0, 28), messages: [user] },
        ...prev,
      ];
    });
    setActive(localId);
    setDraft("");
    setSending(true);
    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          ...(active && !active.startsWith("pending-")
            ? { conversation_id: active }
            : {}),
        }),
      });
      if (!response.ok) {
        let detail = `تعذر الاتصال بالخادم (HTTP ${response.status}).`;
        try {
          const payload = await response.json();
          if (payload.detail) detail = String(payload.detail);
        } catch {}
        throw new Error(detail);
      }
      const data: ApiResponse = await response.json();
      const mappedSources: Source[] = Array.isArray(data.sources)
        ? data.sources.map(mapSource)
        : [];
      const assistant: Message = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: data.answer,
        sources: mappedSources,
      };
      const serverId = data.conversation_id;
      setConversations((prev) =>
        prev.map((c) =>
          c.id === localId
            ? { ...c, id: serverId, messages: [...c.messages, assistant] }
            : c,
        ),
      );
      setActive(serverId);
    } catch (error) {
      const detail =
        error instanceof Error
          ? error.message
          : "حدث خطأ غير متوقع أثناء إرسال السؤال.";
      const assistant: Message = {
        id: `err-${Date.now()}`,
        role: "assistant",
        content: `تعذر الحصول على إجابة من الخادم.\n\n${detail}\n\nتأكد من تشغيل الـ backend، وإعداد مفتاح GROQ_API_KEY، وتشغيل فهرسة البيانات قبل إعادة المحاولة.`,
      };
      setConversations((prev) =>
        prev.map((c) =>
          c.id === localId ? { ...c, messages: [...c.messages, assistant] } : c,
        ),
      );
    } finally {
      setSending(false);
    }
  };
  const feedback = (messageId: string, v: "up" | "down") =>
    setConversations((prev) =>
      prev.map((c) =>
        c.id === active
          ? {
              ...c,
              messages: c.messages.map((m) =>
                m.id === messageId ? { ...m, feedback: v } : m,
              ),
            }
          : c,
      ),
    );
  return (
    <div className="chat-app" dir="rtl">
      <Sidebar
        items={conversations}
        active={active}
        onNew={newChat}
        onSelect={selectConversation}
        open={drawer}
        onClose={() => setDrawer(false)}
        onInfo={() => setHelp((v) => !v)}
      />
      <main className="chat-main">
        <header className="chat-header">
          <button
            className="icon-btn menu-btn"
            onClick={() => setDrawer(true)}
            aria-label="فتح المحادثات"
          >
            <Menu />
          </button>
          <div>
            <h1>{PRODUCT_NAME}</h1>
            <p>{PRODUCT_NAME_EN} · اسأل عن القوانين واللوائح المصرية</p>
          </div>
          <div className="header-actions">
            <button
              className="icon-btn"
              onClick={() => setHelp((v) => !v)}
              aria-label="معلومات عن النسخة"
            >
              <Info />
            </button>
            {help && (
              <div className="help-popover">
                الإجابات تعتمد على قاعدة البيانات المتاحة، ولا تثبت حداثة
                التشريعات أو سريانها. راجع المصدر واستشر محامياً في المسائل
                الخاصة.
              </div>
            )}
          </div>
        </header>
        <section className="conversation-area" ref={scrollRef}>
          {!current || current.messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">
                <Scale size={27} />
              </div>
              <span className="eyebrow">مساحة للاستكشاف القانوني</span>
              <h2>كيف يمكنني مساعدتك اليوم؟</h2>
              <p>
                اطرح سؤالك، وسيبحث المساعد في المقاطع القانونية المفهرسة ويعرض
                المصادر التي استند إليها عند توفر أدلة كافية.
              </p>
              <div className="suggestions">
                {suggestions.map((s) => (
                  <button key={s} onClick={() => submit(s)} disabled={sending}>
                    {s}
                    <ArrowLeft size={15} />
                  </button>
                ))}
              </div>
              <div className="demo-note">
                <Info size={15} /> قاعدة البيانات تجريبية وقد لا تغطي التشريعات
                أو تعديلاتها الحالية.
              </div>
            </div>
          ) : (
            <div className="messages">
              {current.messages.map((m) => (
                <ChatMessage
                  key={m.id}
                  message={m}
                  onFeedback={(v) => feedback(m.id, v)}
                />
              ))}
              {sending && (
                <div className="message-row assistant-row">
                  <div className="assistant-mark">
                    <Logo small />
                  </div>
                  <div className="answer-wrap">
                    <div className="message-content">
                      <p>
                        جارٍ البحث في المصادر القانونية وتحليل المقاطع المسترجعة…
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="اكتب سؤالك القانوني..."
            rows={1}
            aria-label="اكتب سؤالك القانوني"
            disabled={sending}
          />
          <div className="composer-bottom">
            <span>
              {sending
                ? "جارٍ إعداد الإجابة…"
                : "Enter للإرسال · Shift + Enter لسطر جديد"}
            </span>
            <button
              type="submit"
              disabled={!draft.trim() || sending}
              aria-label="إرسال السؤال"
            >
              {sending ? "…" : <Send size={17} />}
            </button>
          </div>
        </form>
        <div className="chat-legal">
          المعلومات لأغراض التوعية فقط، ولا تغني عن استشارة محامٍ مختص.
        </div>
      </main>
    </div>
  );
}
export default function App() {
  const [page, setPage] = useState<"landing" | "chat">(
    window.location.hash === "#chat" ? "chat" : "landing",
  );
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const goChat = () => {
    setPage("chat");
    window.location.hash = "chat";
  };
  useEffect(() => {
    const onHash = () =>
      setPage(window.location.hash === "#chat" ? "chat" : "landing");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return page === "landing" ? (
    <Landing goChat={goChat} />
  ) : (
    <Chat
      conversations={conversations}
      setConversations={setConversations}
      active={active}
      setActive={setActive}
    />
  );
}
