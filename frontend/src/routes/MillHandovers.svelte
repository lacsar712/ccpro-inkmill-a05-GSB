<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import { handoverSlotLabel, millStatusLabel } from '../lib/labels';
  import type { HandoverSlot, Mill, MillHandover, MillStatus } from '../lib/types';

  let rows: MillHandover[] = [];
  let mills: Mill[] = [];
  let error = '';
  let editingId: number | null = null;

  let filterMillId = '';
  let filterDate = '';

  function todayLocal(): string {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 10);
  }

  let form = {
    millId: '',
    shiftDate: todayLocal(),
    slot: 'morning' as HandoverSlot,
    fromOperator: '',
    toOperator: '',
    note: '',
  };

  async function load() {
    error = '';
    try {
      const params = new URLSearchParams();
      if (filterMillId) params.set('millId', filterMillId);
      if (filterDate) params.set('shiftDate', filterDate);
      const qs = params.toString();
      rows = await api<MillHandover[]>(`/mill-handovers${qs ? `?${qs}` : ''}`);
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    }
  }

  async function loadMills() {
    try {
      mills = await api<Mill[]>('/mills');
      if (!form.millId && mills[0]) form.millId = String(mills[0].id);
    } catch (e) {
      error = e instanceof Error ? e.message : '机台加载失败';
    }
  }

  onMount(() => {
    loadMills();
    load();
  });

  $: selectedMill = mills.find((m) => m.id === Number(form.millId)) || null;
  // 只读预览：创建/保存时由服务端写入所选机台的当前 status
  $: snapshotStatus = (selectedMill?.status ?? null) as MillStatus | null;

  function millLabel(id: number): string {
    const m = mills.find((x) => x.id === id);
    return m ? `${m.millCode} (#${m.id})` : `#${id}`;
  }

  function reset() {
    form = {
      millId: mills[0] ? String(mills[0].id) : '',
      shiftDate: todayLocal(),
      slot: 'morning',
      fromOperator: '',
      toOperator: '',
      note: '',
    };
    editingId = null;
  }

  function edit(row: MillHandover) {
    editingId = row.id;
    form = {
      millId: String(row.millId),
      shiftDate: row.shiftDate.slice(0, 10),
      slot: row.slot,
      fromOperator: row.fromOperator,
      toOperator: row.toOperator,
      note: row.note ?? '',
    };
  }

  async function save() {
    error = '';
    const payload = {
      millId: Number(form.millId),
      shiftDate: form.shiftDate,
      slot: form.slot,
      fromOperator: form.fromOperator,
      toOperator: form.toOperator,
      note: form.note,
    };
    try {
      if (editingId) {
        await api(`/mill-handovers/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        });
      } else {
        await api('/mill-handovers', { method: 'POST', body: JSON.stringify(payload) });
      }
      reset();
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : '保存失败';
    }
  }

  async function remove(id: number) {
    if (!confirm('确认删除该交接班记录？')) return;
    try {
      await api(`/mill-handovers/${id}`, { method: 'DELETE' });
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : '删除失败';
    }
  }
</script>

<header class="page-head">
  <h1>机台交接班</h1>
  <p>同机台、同日期、同班次仅一条记录；创建时自动写入当前机台状态快照</p>
</header>

{#if error}
  <div class="err">{error}</div>
{/if}

<section class="panel">
  <h2>{editingId ? '编辑交接班' : '新建交接班'}</h2>
  <div class="fields">
    <div class="field">
      <label>研磨机
        <select bind:value={form.millId}>
          {#each mills as m}
            <option value={String(m.id)}>{m.millCode} · {m.pigmentBase}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field"><label>交接班日期<input type="date" bind:value={form.shiftDate} /></label></div>
    <div class="field">
      <label>班次
        <select bind:value={form.slot}>
          <option value="morning">早班</option>
          <option value="afternoon">中班</option>
          <option value="night">夜班</option>
        </select>
      </label>
    </div>
    <div class="field"><label>交班人<input bind:value={form.fromOperator} placeholder="交出机台的人" /></label></div>
    <div class="field"><label>接班人<input bind:value={form.toOperator} placeholder="接手机台的人" /></label></div>
    <div class="field snapshot">
      <span class="snap-title">机台状态快照（只读）</span>
      {#if snapshotStatus}
        <span class="badge {snapshotStatus}">{millStatusLabel[snapshotStatus]}</span>
      {:else}
        <span class="muted">—</span>
      {/if}
      <span class="muted hint">保存时按机台当前状态自动写入</span>
    </div>
    <div class="field full"><label>备注<input bind:value={form.note} placeholder="机台运行情况、遗留问题（可选）" /></label></div>
  </div>
  <div class="actions">
    <button class="btn-primary" on:click={save}>{editingId ? '保存' : '创建'}</button>
    {#if editingId}
      <button class="btn-ghost" on:click={reset}>取消</button>
    {/if}
  </div>
</section>

<section class="panel">
  <div class="filters">
    <label>机台
      <select bind:value={filterMillId}>
        <option value="">全部机台</option>
        {#each mills as m}
          <option value={String(m.id)}>{m.millCode}</option>
        {/each}
      </select>
    </label>
    <label>日期
      <input type="date" bind:value={filterDate} />
    </label>
    <button class="btn-ghost" on:click={load}>筛选</button>
    {#if filterMillId || filterDate}
      <button class="link-btn" on:click={() => { filterMillId = ''; filterDate = ''; load(); }}>清除筛选</button>
    {/if}
  </div>
  <table class="data-table">
    <thead>
      <tr>
        <th>ID</th>
        <th>研磨机</th>
        <th>日期</th>
        <th>班次</th>
        <th>交班人</th>
        <th>接班人</th>
        <th>状态快照</th>
        <th>备注</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr>
          <td>{row.id}</td>
          <td>{millLabel(row.millId)}</td>
          <td>{row.shiftDate.slice(0, 10)}</td>
          <td>{handoverSlotLabel[row.slot]}</td>
          <td>{row.fromOperator}</td>
          <td>{row.toOperator}</td>
          <td><span class="badge {row.millStatusSnapshot}">{millStatusLabel[row.millStatusSnapshot]}</span></td>
          <td class="note-cell">{row.note ?? ''}</td>
          <td class="ops">
            <button class="link-btn" on:click={() => edit(row)}>编辑</button>
            <button class="link-btn danger" on:click={() => remove(row.id)}>删除</button>
          </td>
        </tr>
      {:else}
        <tr><td colspan="9">暂无交接班记录</td></tr>
      {/each}
    </tbody>
  </table>
</section>

<style>
  .filters {
    display: flex;
    align-items: flex-end;
    gap: 0.8rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }

  .filters label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.85rem;
    color: var(--steel);
  }

  .field.snapshot {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .snap-title {
    font-size: 0.8rem;
    color: var(--steel);
  }

  .field.snapshot .hint {
    font-size: 0.75rem;
  }

  .muted {
    color: var(--steel);
    font-size: 0.85rem;
  }

  .note-cell {
    max-width: 220px;
  }
</style>
