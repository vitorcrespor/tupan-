import React, { useEffect, useState } from 'react';
import { appClient } from '@/demo/localAppClient';
import { useAuth } from '@/lib/AuthContext';
import TopBar from '@/components/tupan/TopBar';
import { Panel, SectionTitle } from '@/components/tupan/primitives';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { UserPlus, Trash2, Loader2, Shield, Lock } from 'lucide-react';

export default function TeamManagement() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('user');
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const res = await appClient.entities.User.list('-created_date', 200);
      setUsers(res || []);
    } catch (e) {
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (isAdmin) load(); else setLoading(false); }, [isAdmin]);

  const invite = async (e) => {
    e.preventDefault();
    if (!email.trim() || inviting) return;
    setInviting(true); setError('');
    try {
      await appClient.users.inviteUser(email.trim(), role);
      setEmail('');
      load();
    } catch (e) {
      setError(e.message || 'Falha ao convidar');
    } finally {
      setInviting(false);
    }
  };

  const changeRole = async (id, newRole) => {
    setError('');
    try {
      await appClient.entities.User.update(id, { role: newRole });
      load();
    } catch (e) {
      setError(e.message || 'Falha ao atualizar papel');
    }
  };

  const remove = async (id) => {
    if (!confirm('Remover este membro da equipe?')) return;
    setError('');
    try {
      await appClient.entities.User.delete(id);
      load();
    } catch (e) {
      setError(e.message || 'Falha ao remover');
    }
  };

  if (!isAdmin) {
    return (
      <>
        <TopBar title="Gestão de Equipe" subtitle="Acesso enterprise" />
        <div className="flex-1 flex items-center justify-center p-5">
          <Panel className="p-8 max-w-md text-center">
            <Lock className="w-8 h-8 mx-auto text-text-muted mb-3" />
            <h2 className="text-lg font-semibold text-foreground">Acesso restrito</h2>
            <p className="text-sm text-text-secondary mt-1">A gestão de equipe é exclusiva para contas enterprise (administradores).</p>
          </Panel>
        </div>
      </>
    );
  }

  return (
    <>
      <TopBar title="Gestão de Equipe" subtitle="Convites, papéis enterprise e permissões" />
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {error && <div className="rounded-xl border border-negative/25 bg-negative/10 text-negative text-sm px-3 py-2">{error}</div>}
        <Panel className="p-4">
          <SectionTitle>Convidar membro</SectionTitle>
          <form onSubmit={invite} className="flex flex-wrap items-center gap-2">
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@empresa.com" className="flex-1 min-w-[220px] h-9 rounded-xl border border-border bg-surface px-3 text-sm outline-none focus:border-brand/40" />
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger className="h-9 w-[180px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="user">Usuário (padrão)</SelectItem>
                <SelectItem value="admin">Enterprise (admin)</SelectItem>
              </SelectContent>
            </Select>
            <button type="submit" disabled={!email.trim() || inviting} className="h-9 px-4 rounded-full bg-brand text-brand-foreground text-sm font-medium flex items-center gap-1.5 disabled:opacity-50">
              {inviting ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
              Convidar
            </button>
          </form>
        </Panel>

        <Panel className="p-4">
          <SectionTitle right={<span className="text-[11px] text-text-muted">{users.length} membros</span>}>Membros da equipe</SectionTitle>
          {loading ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-text-muted" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-text-muted text-left border-b border-border text-[11px] uppercase">
                    <th className="py-2 font-medium">Membro</th>
                    <th>E-mail</th>
                    <th>Papel</th>
                    <th className="text-right">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-border/50">
                      <td className="py-2.5 text-foreground font-medium">{u.full_name || '—'}</td>
                      <td className="text-text-secondary">{u.email}</td>
                      <td>
                        {u.id === user.id ? (
                          <span className="inline-flex items-center gap-1 text-[11px] text-text-muted">
                            {u.role === 'admin' && <Shield className="w-3 h-3" />}
                            {u.role === 'admin' ? 'Enterprise (você)' : 'Usuário (você)'}
                          </span>
                        ) : (
                          <Select value={u.role || 'user'} onValueChange={(v) => changeRole(u.id, v)}>
                            <SelectTrigger className="h-7 w-[170px]"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="user">Usuário</SelectItem>
                              <SelectItem value="admin">Enterprise (admin)</SelectItem>
                            </SelectContent>
                          </Select>
                        )}
                      </td>
                      <td className="text-right">
                        {u.id !== user.id && (
                          <button onClick={() => remove(u.id)} className="w-8 h-8 rounded-full inline-flex items-center justify-center text-text-muted hover:text-negative hover:bg-negative/5 ml-auto">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
