import { Outlet } from 'react-router';
import { Card } from '@/components/domain/primitives';
import { ErrorState, LoadingRows } from '@/components/domain/states';
import { EvidenceDrawer } from '@/features/evidence/EvidenceDrawer';
import { AudioEngine } from '@/features/replay/audio';
import { useReplayDriver } from '@/features/replay/store';
import { useSessionScope } from '@/hooks/useSessionScope';
import { useSessionStream } from '@/hooks/useSessionStream';

/** Loads the session once for all session-scoped screens and keeps the stream connected. */
export function SessionLayout() {
  const { sid, session } = useSessionScope();
  useSessionStream(sid);
  const media = session.data?.media ?? null;
  // DEMO workspaces (ADR 0003): the audio element drives the clock instead of rAF.
  useReplayDriver(!media);
  if (session.isPending)
    return (
      <div className="space-y-5">
        <LoadingRows rows={2} />
        <LoadingRows rows={5} />
      </div>
    );
  if (session.isError)
    return (
      <Card className="mx-auto mt-10 max-w-xl">
        <ErrorState error={session.error} onRetry={() => session.refetch()} />
      </Card>
    );
  return (
    <>
      {media && <AudioEngine key={media.workspace_id} media={media} sessionId={sid} />}
      <Outlet />
      <EvidenceDrawer />
    </>
  );
}
