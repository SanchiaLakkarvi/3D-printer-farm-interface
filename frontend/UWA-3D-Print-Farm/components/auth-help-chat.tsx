"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { MessageCircle, Send, ShieldAlert, Sparkles } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  HelpApiError,
  sendHelpMessage,
  type HelpHistoryMessage,
} from "@/lib/help/client";

const MAX_HISTORY_MESSAGES = 6;
const MAX_MESSAGE_CHARS = 1000;

const HELP_CONTENT = {
  auth: {
    greeting:
      "Hi! I can help with signing in, creating a student account, and email verification. What are you having trouble with?",
    placeholder: "How do I resend my verification code?",
    suggestions: [
      "I can’t sign in",
      "I didn’t receive my verification code",
      "How do I create a student account?",
    ],
  },
  student: {
    greeting:
      "Hi! I can help with uploading files, price estimates, and tracking print jobs. What are you having trouble with?",
    placeholder: "How do I upload a print file?",
    suggestions: [
      "How do I upload a print file?",
      "How is my print price estimated?",
      "How do I track my print job?",
    ],
  },
} as const;

type AuthHelpChatProps = {
  mode?: keyof typeof HELP_CONTENT;
};

export function AuthHelpChat({ mode = "auth" }: AuthHelpChatProps) {
  const content = HELP_CONTENT[mode];
  const [messages, setMessages] = useState<HelpHistoryMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageInputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "nearest" });
  }, [messages, pending]);

  async function ask(message: string) {
    if (!message || pending) return;

    const history = messages.slice(-MAX_HISTORY_MESSAGES);
    setError("");
    setPending(true);
    setDraft("");
    setMessages([...history, { role: "user", content: message }]);
    try {
      const result = await sendHelpMessage(message, history);
      const nextMessages: HelpHistoryMessage[] = [
        ...history,
        { role: "user", content: message },
        { role: "assistant", content: result.message },
      ];
      setMessages(nextMessages.slice(-MAX_HISTORY_MESSAGES));
    } catch (caught) {
      setError(
        caught instanceof HelpApiError
          ? caught.message
          : "Help chat is unavailable. Please try again later.",
      );
    } finally {
      setPending(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(draft.trim());
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button type="button" className="auth-help-trigger">
          <span className="auth-help-trigger-icon">
            <Sparkles />
          </span>
          <span>Ask Print Farm help</span>
          <MessageCircle className="auth-help-trigger-action" />
        </button>
      </DialogTrigger>
      <DialogContent
        className="auth-help-dialog"
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          messageInputRef.current?.focus();
        }}
      >
        <DialogHeader className="auth-help-header">
          <DialogTitle>Having trouble?</DialogTitle>
          <DialogDescription>
            Ask a question and continue the conversation here.
          </DialogDescription>
        </DialogHeader>

        <div className="auth-help-messages" aria-live="polite">
          <div className="auth-help-message assistant">
            <b>Print Farm help</b>
            <p>{content.greeting}</p>
          </div>

          {messages.length === 0 && (
            <div className="auth-help-suggestions" aria-label="Suggested questions">
              {content.suggestions.map((question) => (
                <button
                  type="button"
                  key={question}
                  onClick={() => void ask(question)}
                  disabled={pending}
                >
                  {question}
                </button>
              ))}
            </div>
          )}

          {messages.map((item, index) => (
            <div
              className={`auth-help-message ${item.role}`}
              key={`${item.role}-${index}`}
            >
              <b>{item.role === "user" ? "You" : "Print Farm help"}</b>
              <p>{item.content}</p>
            </div>
          ))}

          {pending && (
            <div className="auth-help-message assistant pending" role="status">
              <b>Print Farm help</b>
              <p>Finding an answer…</p>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="auth-help-warning">
          <ShieldAlert />
          <span>Do not share passwords, confirmation links, or tokens.</span>
        </div>

        <form className="auth-help-form" onSubmit={submit}>
          <label className="sr-only" htmlFor="auth-help-message">
            Your question
          </label>
          <textarea
            ref={messageInputRef}
            id="auth-help-message"
            value={draft}
            maxLength={MAX_MESSAGE_CHARS}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={content.placeholder}
            disabled={pending}
          />
          {error && <div className="error">{error}</div>}
          <button
            className="auth-help-send"
            type="submit"
            aria-label="Send question"
            disabled={pending || !draft.trim()}
          >
            <Send />
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
