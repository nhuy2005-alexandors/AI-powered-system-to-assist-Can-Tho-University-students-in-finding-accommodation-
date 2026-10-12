"""Shared evaluation pause. Quota is not an answer/metric failure or a zero score."""
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
import re, threading


class QuotaPause(BaseException):
    """Evaluation control signal bypassing application fallback and Ragas retries."""


def quota_metadata(response, now=None):
    now=now or datetime.now(timezone.utc)
    delay=60.0
    header=response.headers.get('Retry-After','')
    try:delay=max(delay,float(header))
    except ValueError:
        try:delay=max(delay,(parsedate_to_datetime(header)-now).total_seconds())
        except (ValueError,TypeError):pass
    try:details=response.json().get('error',{}).get('details',[])
    except ValueError:details=[]
    quotas=[]
    for detail in details:
        if 'RetryInfo' in detail.get('@type',''):
            match=re.fullmatch(r'(\d+(?:\.\d+)?)s',detail.get('retryDelay',''))
            if match:delay=max(delay,float(match[1]))
        for item in detail.get('violations',[]):
            quotas.append({k:item.get(k) for k in ('quotaMetric','quotaId','quotaValue')})
    daily=any('perday' in (str(q.get('quotaId'))+' '+str(q.get('quotaMetric'))).lower() for q in quotas)
    if daily:
        pacific=now.astimezone(ZoneInfo('America/Los_Angeles'))
        reset=datetime.combine(pacific.date()+timedelta(days=1),datetime.min.time(),pacific.tzinfo)
        delay=max(delay,(reset.astimezone(timezone.utc)-now).total_seconds()+5)
    return {'status':'paused','http_status':429,'paused_at_utc':now.isoformat(),
            'retry_at_utc':(now+timedelta(seconds=delay)).isoformat(),'delay_seconds':delay,
            'daily_quota':daily,'quota':quotas,
            'reset_policy':'server Retry-After/RetryInfo; RPD midnight America/Los_Angeles; probe availability before resuming'}


class QuotaCoordinator:
    def __init__(self):self.state=None;self.lock=threading.Lock()
    @property
    def paused(self):return self.state is not None
    def request_hook(self, request):
        if self.paused:raise QuotaPause('Gemini evaluation paused at quota checkpoint')
    def response_hook(self, response):
        if response.status_code!=429:return
        response.read()
        with self.lock:
            new=quota_metadata(response)
            if self.state is None or new['retry_at_utc']>self.state['retry_at_utc']:self.state=new
        raise QuotaPause('Gemini HTTP 429; checkpoint required')
    def attach(self, generator):
        generator._client.event_hooks.setdefault('request',[]).append(self.request_hook)
        generator._client.event_hooks.setdefault('response',[]).append(self.response_hook)


def bounded_scoring(tasks, worker, on_result, coordinator, workers):
    """Only at most workers jobs are in flight; drain real successes on a pause."""
    from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
    iterator=iter(tasks);pending={};paused=False
    with ThreadPoolExecutor(max_workers=workers) as pool:
        def submit():
            if coordinator.paused:return
            try:task=next(iterator)
            except StopIteration:return
            pending[pool.submit(worker,*task)]=task
        for _ in range(workers):submit()
        while pending:
            done,_=wait(pending,return_when=FIRST_COMPLETED)
            for future in done:
                task=pending.pop(future)
                try:on_result(task,future.result())
                except QuotaPause:paused=True
            if not coordinator.paused and not paused:
                for _ in done:submit()
    if coordinator.paused or paused:raise QuotaPause('Scoring paused; valid results saved')


def checkpoint_pause(report,output,coordinator,phase):
    from question_bank_ragas import summarize,save_report
    report['quota_state']=dict(coordinator.state or {},phase=phase)
    summarize(report);save_report(output,report)
