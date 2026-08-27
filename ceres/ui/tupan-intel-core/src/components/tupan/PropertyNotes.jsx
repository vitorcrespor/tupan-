import React, { useState, useEffect, useCallback } from 'react';
import { appClient } from '@/demo/localAppClient';
import { useAuth } from '@/lib/AuthContext';
import { MessageSquare, Send, Loader2, Lock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export default function PropertyNotes({ propertyId }) {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await appClient.entities.PropertyNote.filter({ property_id: propertyId }, '-created_date', 100);
      setNotes(Array.isArray(res) ? res : []);
    } catch (e) {
      setNotes([]);
    } finally {
      setLoading(false);
    }
  }, [propertyId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const unsub = appClient.entities.PropertyNote.subscribe((event) => {
      if (event?.data?.property_id === propertyId) load();
    });
    return unsub;
  }, [propertyId, load]);

  const submit = async (e) => {
    e.preventDefault();
    if (!text.trim() || sending) return;
    setSending(true);
    try {
      await appClient.entities.PropertyNote.create({
        property_id: propertyId,
        content: text.trim(),
        author_name: user?.full_name || user?.email || 'Corretor',
      });
      setText('');
      load();
    } catch (e) {
      // RLS rejects non-admins; surfaced silently
    } finally {
      setSending(false);
    }
  };

  const count = notes.length;

  return (
    <div className="pt-4" onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface/70 px-3 py-1.5 text-[12px] font-medium text-text-secondary hover:text-foreground hover:border-brand/30 transition-colors"
      >
        <MessageSquare className="w-3.5 h-3.5" />
        Notas da equipe
        {count > 0 && (
          <span className="ml-0.5 inline-flex items-center justify-center rounded-full bg-brand/15 text-brand text-[10px] font-semibold px-1.5">
            {count}
          </span>
        )}
      </button>

      {open && (
        <div className="mt-3 rounded-2xl border border-border bg-elevated/60 p-3">
          {loading ? (
            <div className="flex items-center justify-center py-3 text-text-muted">
              <Loader2 className="w-4 h-4 animate-spin" />
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-2.5 max-h-44 overflow-y-auto pr-1">
                {notes.length === 0 && (
                  <p className="text-[12px] text-text-muted py-2 text-center">Nenhuma nota ainda.</p>
                )}
                {notes.map((n) => (
                  <div key={n.id} className="flex flex-col gap-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-foreground">{n.author_name || 'Corretor'}</span>
                      <span className="text-[10px] text-text-muted">
                        {n.created_date ? formatDistanceToNow(new Date(n.created_date), { addSuffix: true, locale: ptBR }) : ''}
                      </span>
                    </div>
                    <p className="m-0 text-[12px] leading-5 text-text-secondary whitespace-pre-wrap break-words">{n.content}</p>
                  </div>
                ))}
              </div>

              {isAdmin ? (
                <form onSubmit={submit} className="mt-3 flex items-center gap-2">
                  <input
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Escrever uma nota para a equipe…"
                    className="flex-1 h-9 rounded-full border border-border bg-surface px-3 text-[12px] text-foreground outline-none placeholder:text-text-muted focus:border-brand/40"
                  />
                  <button
                    type="submit"
                    disabled={!text.trim() || sending}
                    className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-brand text-brand-foreground disabled:opacity-40 hover:brightness-105 transition"
                  >
                    {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  </button>
                </form>
              ) : (
                <p className="mt-3 flex items-center gap-1.5 text-[11px] text-text-muted">
                  <Lock className="w-3 h-3" /> Somente contas enterprise podem deixar notas.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
