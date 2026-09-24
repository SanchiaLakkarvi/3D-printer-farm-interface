"use client";
import "./upload.css";
import "./farm.css";
import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, BarChart3, Bell, CheckCircle2, CircleHelp, CreditCard, FileText, Gauge, GraduationCap, HardHat, LayoutDashboard, LockKeyhole, LogOut, Mail, Menu, Printer, ShieldCheck, Sparkles, Upload, UserCog, Users, Wrench, X, Eye, EyeOff, Building2 } from "lucide-react";
import { AuthApiError, AUTH_GENERIC_ERROR, getApiBaseUrl, resolveDepartment, restoreSession, signInWithRoleMatch, signOut, signupStudent, type UserProfile } from "@/lib/auth/client";
import { clearAccessToken } from "@/lib/auth/session";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { LiveDashboard } from "@/components/farm/live-dashboard";
import { LiveQueue } from "@/components/farm/live-queue";
type Role = "student" | "farmer" | "admin"; type Screen = "welcome" | "login" | "signup" | "dashboard";
function isRole(value: string): value is Role { return value === "student" || value === "farmer" || value === "admin" }
function initialsFor(profile: UserProfile | null, fallback: string) { if (!profile) return fallback; const a = (profile.first_name[0] ?? "").toUpperCase(), b = (profile.last_name[0] ?? "").toUpperCase(); return (a + b) || fallback }
const roles = {
  student: {
    title: "Student",
    sub: "Submit and track your 3D print jobs",
    domain: "@student.uwa.edu.au",
    example: "student@student.uwa.edu.au",
    name: "Student",
    initials: "ST",
    icon: GraduationCap,
  },
  farmer: {
    title: "Printer Farmer",
    sub: "Manage print jobs and farm operations",
    domain: "@uwa.edu.au",
    example: "operator@uwa.edu.au",
    name: "Printer Farmer",
    initials: "PF",
    icon: HardHat,
  },
  admin: {
    title: "Administrator",
    sub: "Manage printers, users and reporting",
    domain: "@uwa.edu.au",
    example: "admin@uwa.edu.au",
    name: "Administrator",
    initials: "AD",
    icon: ShieldCheck,
  },
};
const SIGNUP_PASSWORD_MIN_LENGTH = 8;
const menus = { student: [["Dashboard", LayoutDashboard], ["Upload file", Upload], ["My jobs", FileText], ["Shared queue", Users], ["Notifications", Bell], ["Usage & costs", BarChart3], ["Help & support", CircleHelp]], farmer: [["Dashboard", LayoutDashboard], ["Farm operations", Gauge], ["Upload file", Upload], ["Notifications", Bell], ["Jobs", FileText], ["Shared queue", Users], ["Maintenance", Wrench]], admin: [["Dashboard", LayoutDashboard], ["Farm operations", Gauge], ["Upload file", Upload], ["Notifications", Bell], ["Jobs", FileText], ["Shared queue", Users], ["Maintenance", Wrench], ["Usage reports", BarChart3], ["Users & access", UserCog]] } as const;
const descriptions: Record<string, string> = { "Upload file": "Upload a pre-sliced G-code file and review its print job summary.", "My jobs": "Review active, completed and cancelled jobs, with print progress, printer details and collection status.", "Jobs": "Review submissions, validation results, queue state, print progress and collection status across the farm.", "Shared queue": "View compatible jobs in submission order and see estimated waiting times without exposing private student files.", "Notifications": "Print-start, completion and collection messages will appear here and can also be delivered by email.", "Usage & costs": "See how print time is converted into an estimated cost before payment.", "Help & support": "Find G-code preparation guidance, collection instructions and contact details for the Print Farm team.", "Farm operations": "Move jobs through printing, removal, packing and ready-for-collection stages from one operational view.", "Maintenance": "Record maintenance, printer downtime and service notes so the team knows which machines are available.", "Usage reports": "Compare print hours, jobs, filament and indicative costs by department, printer and date range.", "Users & access": "Manage authorised students, printer farmers and administrators with role-based access." };
function Brand() { return <div className="brand"><span className="logo"><Printer /></span><span><b>UWA 3D Print Farm</b></span></div> }
export default function Home() {
  const [screen, setScreen] = useState<Screen>("welcome"), [role, setRole] = useState<Role>("student"), [email, setEmail] = useState(""), [password, setPassword] = useState(""), [show, setShow] = useState(false), [error, setError] = useState(""), [notice, setNotice] = useState(""), [active, setActive] = useState("Dashboard"), [nav, setNav] = useState(false), [profile, setProfile] = useState<UserProfile | null>(null), [pending, setPending] = useState(false), [restoring, setRestoring] = useState(true);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const user = await restoreSession();
        if (cancelled) return;
        if (user && isRole(user.role)) {
          setProfile(user);
          setRole(user.role);
          setEmail(user.email);
          setActive("Dashboard");
          setScreen("dashboard");
        }
      } finally {
        if (!cancelled) setRestoring(false);
      }
    })();
    return () => { cancelled = true };
  }, []);
  function choose(x: Role) { setRole(x); setEmail(""); setPassword(""); setError(""); setNotice(""); setProfile(null); setScreen("login") }
  async function login(e: FormEvent) { e.preventDefault(); setError(""); setNotice(""); setPending(true); try { const user = await signInWithRoleMatch(email.trim(), password, role); if (!isRole(user.role)) throw new AuthApiError(AUTH_GENERIC_ERROR, 500); setProfile(user); setRole(user.role); setEmail(user.email); setPassword(""); setActive("Dashboard"); setScreen("dashboard") } catch (err) { setError(err instanceof AuthApiError ? err.message : AUTH_GENERIC_ERROR) } finally { setPending(false) } }
  async function logout() { await signOut(); setProfile(null); setScreen("welcome"); setEmail(""); setPassword(""); setError(""); setNotice(""); setActive("Dashboard") }
  if (restoring) return <main className="auth welcome"><div className="wrap"><Brand /><p>Restoring your session…</p></div></main>;
  if (screen === "welcome") return <Welcome choose={choose} />;
  if (screen === "login") return <Login role={role} email={email} password={password} show={show} error={error} notice={notice} pending={pending} setEmail={setEmail} setPassword={setPassword} setShow={setShow} submit={login} back={() => setScreen("welcome")} signup={role === "student" ? () => { setEmail(""); setPassword(""); setError(""); setNotice(""); setScreen("signup") } : undefined} />;
  if (screen === "signup") { if (role !== "student") return <Login role={role} email={email} password={password} show={show} error={error} notice={notice} pending={pending} setEmail={setEmail} setPassword={setPassword} setShow={setShow} submit={login} back={() => setScreen("welcome")} />; return <Signup back={() => { setEmail(""); setPassword(""); setError(""); setNotice(""); setScreen("login") }} goSignIn={(address, message) => { setRole("student"); setEmail(address); setPassword(""); setError(""); setNotice(message); setScreen("login") }} />; }
  if (!profile) return <Welcome choose={choose} />;
  const shellRole = isRole(profile.role) ? profile.role : role; const shellMeta = roles[shellRole]; const shellEmail = profile.email; const shellName = `${profile.first_name} ${profile.last_name}`.trim(); const shellInitials = initialsFor(profile, shellMeta.initials);
  return <div className="shell"><header><button className="hamb" onClick={() => setNav(true)}><Menu /></button><Brand /><div className="top-user"><span><b>{shellName}</b><small>{shellEmail}</small></span><i className={"avatar " + shellRole}>{shellInitials}</i></div></header><aside className={nav ? "open" : ""}><button className="close" onClick={() => setNav(false)}><X /></button><nav>{menus[shellRole].map(([label, Icon]) => <button key={label} className={active === label ? "active" : ""} onClick={() => { setActive(label); setNav(false) }}><Icon />{label}</button>)}</nav><div className="account"><div><i>{shellInitials}</i><span><b>{shellMeta.title} account</b><small>{shellEmail}</small></span></div><button onClick={logout}><LogOut />Log out</button></div></aside>{nav && <button className="shade" onClick={() => setNav(false)} />}<main className="work">{active === "Dashboard" ? <LiveDashboard role={shellRole} profile={profile} upload={() => setActive("Upload file")} openJobs={() => setActive(shellRole === "student" ? "My jobs" : "Jobs")} /> : <Feature role={shellRole} active={active} />}</main></div>
}
function Welcome({ choose }: { choose: (r: Role) => void }) { return <main className="auth welcome"><div className="wrap"><Brand /><section className="hero"><span><Sparkles /> UWA printing made simple</span><h1>Get started with the<br /><em>3D Print Farm</em></h1><p>Upload your files, follow your print job and know when it is ready to collect.</p></section><section className="access"><div><span>ACCESS THE PORTAL</span><h2>Continue as</h2><p>Select the option for your UWA account.</p></div><div className="cards">{(["student", "farmer", "admin"] as Role[]).map(k => { const v = roles[k], Icon = v.icon; return <button key={k} className={k} onClick={() => choose(k)}><i><Icon /></i><span><h3>{v.title}</h3><p>{v.sub}</p><small>{v.domain}</small></span><ArrowRight /></button> })}</div></section><footer><span>University of Western Australia</span><span>Need help? Contact the Print Farm team</span></footer></div></main> }
function VerifyStory() {
  return (
    <section className="story">
      <Brand />
      <div>
        <span>UWA 3D PRINT FARM</span>
        <h1>One more step<br />before you print.</h1>
        <p>Confirm your student email so we know it is really you, then sign in to start uploading G-code.</p>
        <div className="steps">
          <b>01<small>Open your inbox</small></b>
          <b>02<small>Enter the code</small></b>
          <b>03<small>Sign in</small></b>
        </div>
      </div>
      
    </section>
  );
}
type LP = { role: Role; email: string; password: string; show: boolean; error: string; notice?: string; pending: boolean; setEmail: (x: string) => void; setPassword: (x: string) => void; setShow: (x: boolean) => void; submit: (e: FormEvent) => void; back: () => void; signup?: () => void };
function Login(p: LP) { const r = roles[p.role], Icon = r.icon; const emailHint = p.role === "student" ? `Use your ${r.domain} email` : "Use the email on your Print Farm account"; return <main className="auth split"><section className="story"><Brand /><div><span>UWA 3D PRINT FARM</span><h1>Turn your design<br />into something real.</h1><p>A simple way to submit, track and collect your UWA 3D prints.</p><div className="steps"><b>01<small>Upload G-code</small></b><b>02<small>Join the queue</small></b><b>03<small>Collect your print</small></b></div></div></section><section className="formside"><div className="formcard"><button className="back" onClick={p.back}><ArrowLeft />Back</button><i className={"roleicon " + p.role}><Icon /></i><span className="kicker">{r.title} access</span><h2>Welcome back</h2><p>Sign in with your UWA account to continue.</p><form onSubmit={p.submit}><label>Email address<div className="input"><Mail /><input type="email" value={p.email} onChange={e => p.setEmail(e.target.value)} placeholder={r.domain} required /></div><small>{emailHint}</small></label><label>Password<div className="input"><LockKeyhole /><input type={p.show ? "text" : "password"} value={p.password} onChange={e => p.setPassword(e.target.value)} placeholder="Enter your password" required /><button type="button" onClick={() => p.setShow(!p.show)}>{p.show ? <EyeOff /> : <Eye />}</button></div></label>{p.notice && <div className="notice">{p.notice}</div>}{p.error && <div className="error">{p.error}</div>}<button className="primary" disabled={p.pending}>{p.pending ? "Signing in…" : <>Sign in <ArrowRight /></>}</button></form>{p.role === "student" && p.signup ? <div className="join">New to the Print Farm? <button type="button" onClick={p.signup}>Create a student account</button></div> : <div className="staff"><ShieldCheck />{r.title} accounts are issued by an authorised administrator.</div>}</div></section></main> }

async function signupCodeRequest(path: string, payload: object): Promise<{ message: string }> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body && typeof body === "object" && "detail" in body ? body.detail : null;
    const message = typeof detail === "string" ? detail :
      detail && typeof detail === "object" && "message" in detail && typeof detail.message === "string"
        ? detail.message : AUTH_GENERIC_ERROR;
    throw new AuthApiError(message, response.status);
  }
  const message = body && typeof body === "object" && "message" in body && typeof body.message === "string"
    ? body.message : "";
  return { message };
}
function verifySignupCode(email: string, code: string) {
  return signupCodeRequest("/api/auth/verify-signup-code", { email, code });
}
function resendSignupCode(email: string) {
  return signupCodeRequest("/api/auth/resend-signup-code", { email });
}

function Signup({ back, goSignIn }: { back: () => void; goSignIn: (email: string, message: string) => void }) {
  const [f, setF] = useState({ first: "", last: "", email: "", dept: "", other: "", pass: "" });
  const [err, setErr] = useState("");
  const [verifyNotice, setVerifyNotice] = useState("");
  const [pending, setPending] = useState(false);
  const [pendingEmail, setPendingEmail] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [resendWait, setResendWait] = useState(0);
  useEffect(() => {
    if (resendWait <= 0) return;
    const timer = window.setInterval(() => setResendWait((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [resendWait]);
  function u(k: string, v: string) { setF({ ...f, [k]: v }); }
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (f.dept === "Other" && !f.other.trim()) return setErr("Please specify your department.");
    if (f.pass.length < SIGNUP_PASSWORD_MIN_LENGTH) return setErr(`Password must contain at least ${SIGNUP_PASSWORD_MIN_LENGTH} characters.`);
    setErr("");
    setPending(true);
    try {
      const result = await signupStudent({ first_name: f.first.trim(), last_name: f.last.trim(), email: f.email.trim(), password: f.pass, department: resolveDepartment(f.dept, f.other) });
      clearAccessToken();
      setPendingEmail(result.email);
      setCode("");
      setVerifyNotice(result.message);
      setResendWait(60);
    } catch (error) {
      setErr(error instanceof AuthApiError ? error.message : AUTH_GENERIC_ERROR);
    } finally {
      setPending(false);
    }
  }
  async function verify(e: FormEvent) {
    e.preventDefault();
    if (!pendingEmail || code.length !== 6) return setErr("Enter the six-digit verification code.");
    setErr("");
    setVerifyNotice("");
    setPending(true);
    try {
      const result = await verifySignupCode(pendingEmail, code);
      goSignIn(pendingEmail, result.message);
    } catch (error) {
      setErr(error instanceof AuthApiError ? error.message : AUTH_GENERIC_ERROR);
    } finally {
      setPending(false);
    }
  }
  async function resend() {
    if (!pendingEmail || resendWait > 0) return;
    setErr("");
    setVerifyNotice("");
    setPending(true);
    try {
      const result = await resendSignupCode(pendingEmail);
      setVerifyNotice(result.message);
      setResendWait(60);
    } catch (error) {
      setErr(error instanceof AuthApiError ? error.message : AUTH_GENERIC_ERROR);
    } finally {
      setPending(false);
    }
  }
  const depts = ["Mechanical Engineering", "Electrical Engineering", "Civil Engineering", "Computer Science & Software Engineering", "Architecture & Design", "Other"];
  if (pendingEmail) return (
    <main className="auth split">
      <VerifyStory />
      <section className="formside">
        <div className="formcard">
          <i className="roleicon student"><Mail /></i>
          <span className="kicker">Check your inbox</span>
          <h2>Let&apos;s verify your email</h2>
          <p>We sent a six-digit verification code to</p>
          <p className="verify-address">{pendingEmail}</p>
          <p className="verify-hint">Enter the code below. You will use your password whenever you sign in later.</p>
          <form onSubmit={verify} className="otp-form">
            <label>Verification code</label>
            <InputOTP maxLength={6} value={code} onChange={(value) => setCode(value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" autoFocus>
              <InputOTPGroup className="otp-group">
                {[0, 1, 2, 3, 4, 5].map((index) => <InputOTPSlot className="otp-slot" index={index} key={index} />)}
              </InputOTPGroup>
            </InputOTP>
            {verifyNotice && <div className="notice">{verifyNotice}</div>}
            {err && <div className="error">{err}</div>}
            <button type="submit" className="primary" disabled={pending || code.length !== 6}>
              {pending ? "Verifying…" : <>Verify email <ArrowRight /></>}
            </button>
          </form>
          <div className="verify-links">
            <button type="button" disabled={pending || resendWait > 0} onClick={resend}>
              {resendWait > 0 ? `Resend code in ${resendWait}s` : "Resend code"}
            </button>
            <button type="button" onClick={() => { setPendingEmail(null); setCode(""); setErr(""); setVerifyNotice(""); }}>Change email</button>
          </div>
        </div>
      </section>
    </main>
  );
  return <main className="auth signup"><div className="signupwrap"><div className="signuptop"><Brand /><button className="back" onClick={back}><ArrowLeft />Back to sign in</button></div><div className="signgrid"><section><span className="eyebrow"><Sparkles /> STUDENT REGISTRATION</span><h1>Create your<br />Print Farm account</h1><p>Register once with your UWA student details. Your department is saved to your profile and won’t be requested every time you sign in.</p><div className="benefits"><span><CheckCircle2 />Track every print job</span><span><CheckCircle2 />Receive collection notifications</span><span><CheckCircle2 />View usage and cost estimates</span></div></section><section className="signupcard"><h2>Your student details</h2><p>Use the same details associated with your UWA account.</p><form onSubmit={submit}><div className="two"><label>First name<input value={f.first} onChange={e => u("first", e.target.value)} required /></label><label>Last name<input value={f.last} onChange={e => u("last", e.target.value)} required /></label></div><label>Student email<div className="input"><Mail /><input type="email" value={f.email} onChange={e => u("email", e.target.value)} placeholder="@student.uwa.edu.au" required /></div></label><label>Department<div className="input"><Building2 /><select value={f.dept} onChange={e => u("dept", e.target.value)} required><option value="">Select your department</option>{depts.map(d => <option key={d}>{d}</option>)}</select></div></label>{f.dept === "Other" && <label>Specify department<input value={f.other} onChange={e => u("other", e.target.value)} required /></label>}<label>Password<input type="password" value={f.pass} onChange={e => u("pass", e.target.value)} placeholder={`Minimum ${SIGNUP_PASSWORD_MIN_LENGTH} characters`} required minLength={SIGNUP_PASSWORD_MIN_LENGTH} /></label>{err && <div className="error">{err}</div>}<button className="primary" disabled={pending}>{pending ? "Creating account…" : <>Create student account <ArrowRight /></>}</button></form></section></div></div></main>;
}
const cost = (h: number, m: number) => 2 + Math.max(0, h + m / 60 - 1) * .5;
function CostCard({ pay, file }: { pay?: () => void; file?: boolean }) { return <section className="panel cost"><span>HOW YOUR COST IS CALCULATED</span><h2>How your cost is calculated</h2><div><b>First hour</b><strong>$2.00</strong></div><div><b>Each additional hour</b><strong>$0.50 per hour</strong></div><p>4 hr 22 min = $2.00 + (3 hr 22 min × $0.50) = <b>{`${cost(4, 22).toFixed(2)}`}</b></p>{file && <button className="primary pay" onClick={pay}><CreditCard />Pay securely with Stripe</button>}</section> }
function UploadFeature({ role }: { role: Role }) { const ref = useRef<HTMLInputElement>(null), [name, setName] = useState(""), [err, setErr] = useState(""), [paymentError, setPaymentError] = useState(""); function selected(e: ChangeEvent<HTMLInputElement>) { const f = e.target.files?.[0]; if (!f) return; if (!/\\.(gcode|bgcode)$/i.test(f.name)) { setName(""); setErr("Please choose a .gcode or .bgcode file."); return } setErr(""); setName(f.name) } async function pay() { setPaymentError(""); try { const response = await fetch("/api/checkout", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fileName: name }) }); const data = await response.json(); if (!response.ok || !data.url) throw new Error(data.error || "Payment could not be started."); window.location.assign(data.url) } catch (e) { setPaymentError(e instanceof Error ? e.message : "Payment could not be started.") } } return <><div className="heading"><div><span>{roles[role].title} portal</span><h1>Upload file</h1><p>{descriptions["Upload file"]}</p></div><button onClick={() => ref.current?.click()}><Upload />Choose G-code file</button></div><section className="upload-panel"><input ref={ref} className="file-input" type="file" accept=".gcode,.bgcode" onChange={selected} /><button className="drop-zone" onClick={() => ref.current?.click()}><i><Upload /></i><b>{name || "Choose a G-code file"}</b><small>.gcode and .bgcode files are accepted</small></button>{err && <div className="error">{err}</div>}{name && <div className="summary-grid"><section className="panel summary"><span>PRINT JOB SUMMARY</span><h2>Print Job Summary</h2><dl><div><dt>File</dt><dd>{name}</dd></div><div><dt>Printer</dt><dd>Prusa CORE One</dd></div><div><dt>Material</dt><dd>PLA White</dd></div><div><dt>Estimated time</dt><dd>4 hr 22 min</dd></div><div><dt>Estimated filament</dt><dd>47 g</dd></div><div><dt>Queue</dt><dd>Lab A</dd></div><div className="total"><dt>Estimated cost</dt><dd>{`${cost(4, 22).toFixed(2)}`}</dd></div></dl></section><div><CostCard pay={pay} file />{paymentError && <div className="error payment-error">{paymentError}</div>}</div></div>}</section></> }
function Feature({ role, active }: { role: Role; active: string }) { if (["My jobs", "Jobs", "Shared queue", "Farm operations"].includes(active)) return <LiveQueue role={role} view={active} />; if (active === "Upload file") return <UploadFeature role={role} />; if (active === "Usage & costs") return <><div className="heading"><div><span>{roles[role].title} portal</span><h1>Usage & costs</h1><p>{descriptions[active]}</p></div></div><CostCard /></>; const pair = menus[role].find(([x]) => x === active)!, I = pair[1]; return <><div className="heading"><div><span>{roles[role].title} portal</span><h1>{active}</h1><p>{descriptions[active]}</p></div></div><section className="feature"><i><I /></i><span>{active.toUpperCase()}</span><h2>{active}</h2><p>{descriptions[active]}</p><button>View details <ArrowRight /></button></section></> }
