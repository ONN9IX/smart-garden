"use client";
import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { platformApi, PlatformError } from "@/lib/api/platform";
import type {
  CreateOrganization,
  PlatformAudit,
  PlatformIdentity,
  PlatformOrganization,
  PlatformOverview,
  Provisioning,
  Subscription,
} from "@/types/platform";
import { organizationTerms } from "@/lib/organization-terminology";

type View = "overview" | "organizations" | "new" | "detail";
const statuses: Record<string, string> = {
  active: "Активен",
  blocked: "Заблокирован",
  archived: "Архив",
  trial: "Пробный период",
  past_due: "Период оплаты истёк",
  cancel_at_period_end: "Отмена в конце периода",
  cancelled: "Отменена",
};
const onboarding: Record<string, string> = {
  not_platform_provisioned: "Создан ранее",
  password_change_required: "Ожидается смена пароля директора",
  active: "Директор активирован",
  blocked: "Директор заблокирован",
};
const actions: Record<string, string> = {
  "organization.create": "Сад зарегистрирован",
  "organization.block": "Сад заблокирован",
  "organization.unblock": "Сад разблокирован",
  "subscription.update": "Подписка изменена",
  "auth.login": "Вход с MFA",
  "auth.logout": "Выход",
  "auth.step_up": "MFA подтверждена",
  "auth.failure": "Неуспешная проверка",
  "operator.create": "Владелец создан",
  "operator.recover": "Доступ восстановлен",
};
const initialSubscription = (): Subscription => ({
  status: "trial",
  plan_code: "standard",
  currency: "RUB",
  interval: "monthly",
  price_minor: 0,
  trial_ends_at: new Date(Date.now() + 14 * 86400000).toISOString(),
  period_start: null,
  period_end: null,
});
const message = (reason: unknown) =>
  reason instanceof Error ? reason.message : "Запрос недоступен.";

export function OwnerConsole({
  view,
  organizationId = "",
}: {
  view: View;
  organizationId?: string;
}) {
  const router = useRouter();
  const [identity, setIdentity] = useState<PlatformIdentity | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const [items, setItems] = useState<PlatformOrganization[]>([]);
  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [selected, setSelected] = useState<PlatformOrganization | null>(null);
  const [events, setEvents] = useState<PlatformAudit[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [mfa, setMfa] = useState("");
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  useEffect(() => {
    const request = ++generation.current;
    let active = true;
    void Promise.resolve().then(async () => {
      if (!active) return;
      setLoading(true);
      setSelected(null);
      setItems([]);
      setOverview(null);
      setEvents([]);
      setError("");
      try {
        const current = await platformApi.me();
        if (!active || request !== generation.current) return;
        setIdentity(current);
        if (view === "overview") {
          const result = await platformApi.overview();
          if (active && request === generation.current) setOverview(result);
        }
        if (view === "organizations") {
          const result = await platformApi.organizations(search, status);
          if (active && request === generation.current) setItems(result);
        }
        if (view === "detail") {
          const result = await platformApi.organization(organizationId);
          if (
            active &&
            request === generation.current &&
            result.id === organizationId
          )
            setSelected(result);
        }
        if (view === "overview" || view === "detail") {
          const result = await platformApi.audit(
            view === "detail" ? organizationId : undefined,
          );
          if (active && request === generation.current) setEvents(result);
        }
      } catch (reason) {
        if (!active || request !== generation.current) return;
        if (reason instanceof PlatformError && reason.status === 401) {
          platformApi.clear();
          setIdentity(null);
          router.replace("/platform/login");
        } else setError(message(reason));
      } finally {
        if (active && request === generation.current) setLoading(false);
      }
    });
    return () => {
      active = false;
      generation.current += 1;
    };
  }, [view, organizationId, revision, search, status, router]);
  async function stepUp(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      setIdentity(await platformApi.stepUp(mfa));
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(false);
      setMfa("");
    }
  }
  async function logout() {
    if (busy) return;
    setBusy(true);
    try {
      await platformApi.logout();
      setIdentity(null);
      router.replace("/platform/login");
    } catch (reason) {
      setError(message(reason));
      setBusy(false);
    }
  }
  if (!identity)
    return (
      <main className="platform-console">
        <p role="status">Проверяем доступ владельца…</p>
        {error && <p role="alert">{error}</p>}
      </main>
    );
  return (
    <main className="platform-console">
      <header className="platform-heading">
        <h1>ПРОМАКС · Владелец платформы</h1>
        <span>{identity.username}</span>
        <button
          className="button secondary"
          disabled={busy}
          onClick={() => void logout()}
        >
          Выйти
        </button>
      </header>
      <nav className="platform-nav" aria-label="Кабинет владельца">
        <Link href="/platform">Обзор</Link>
        <Link href="/platform/organizations">Детские сады</Link>
        <Link href="/platform/organizations/new">Регистрация сада</Link>
      </nav>
      {error && <p role="alert">{error}</p>}
      {loading && <p role="status">Загрузка…</p>}
      <form className="platform-form" onSubmit={(event) => void stepUp(event)}>
        <label>
          Свежий код MFA для привилегированных действий
          <input
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            required
            value={mfa}
            onChange={(event) => setMfa(event.target.value)}
          />
        </label>
        <button className="button secondary" disabled={busy}>
          Подтвердить полномочия
        </button>
        <small>
          Повторно использованный код не принимается. Дождитесь следующего кода
          приложения-аутентификатора.
        </small>
      </form>
      {view === "overview" && overview && (
        <section className="platform-panel">
          <h2>Обзор организаций</h2>
          <div className="platform-grid">
            {Object.entries(overview.organizations).map(([key, count]) => (
              <p key={key}>
                {statuses[key]}: <strong>{count}</strong>
              </p>
            ))}
          </div>
          <p>
            Директоров ожидают смены пароля: {overview.pending_director_setup}
          </p>
          <h3>Подписки</h3>
          {Object.entries(overview.subscriptions).map(([key, count]) => (
            <p key={key}>
              {statuses[key]}: {count}
            </p>
          ))}
        </section>
      )}
      {view === "organizations" && (
        <section className="platform-panel">
          <h2>Детские сады</h2>
          <div className="platform-form">
            <label>
              Поиск по названию
              <input
                maxLength={200}
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <label>
              Статус
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                <option value="">Все</option>
                {["active", "blocked", "archived"].map((key) => (
                  <option key={key} value={key}>
                    {statuses[key]}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {!loading && items.length === 0 && <p>Организации не найдены.</p>}
          <ul className="platform-list">
            {items.map((item) => (
              <li key={item.id}>
                <Link href={`/platform/organizations/${item.id}`}>
                  {item.name}
                </Link>
                <span>
                  {statuses[item.status]} · {onboarding[item.onboarding_status]}
                </span>
                <small>
                  {item.timezone} ·{" "}
                  {new Date(item.created_at).toLocaleDateString("ru-RU")}
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}
      {view === "new" && (
        <CreateGarden enabled={identity.credential_handoff_enabled} />
      )}
      {view === "detail" && selected?.id === organizationId && (
        <GardenDetail
          key={organizationId}
          garden={selected}
          onChanged={() => setRevision((value) => value + 1)}
        />
      )}
      {(view === "overview" || view === "detail") && (
        <section className="platform-panel">
          <h2>Аудит владельца</h2>
          {events.length === 0 ? (
            <p>Событий нет.</p>
          ) : (
            <ul className="platform-list">
              {events.map((item) => (
                <li key={item.id}>
                  <strong>
                    {actions[item.action] || "Действие владельца"}
                  </strong>
                  <time>
                    {new Date(item.created_at).toLocaleString("ru-RU")}
                  </time>
                  {item.organization_id && (
                    <Link
                      href={`/platform/organizations/${item.organization_id}`}
                    >
                      Организация
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}

function SubscriptionFields({
  value,
  change,
}: {
  value: Subscription;
  change: (value: Subscription) => void;
}) {
  return (
    <div className="platform-form">
      <label>
        Статус подписки
        <select
          value={value.status}
          onChange={(event) =>
            change({
              ...value,
              status: event.target.value as Subscription["status"],
            })
          }
        >
          {[
            "trial",
            "active",
            "past_due",
            "cancel_at_period_end",
            "cancelled",
          ].map((status) => (
            <option key={status} value={status}>
              {statuses[status]}
            </option>
          ))}
        </select>
      </label>
      <label>
        Интервал
        <select
          value={value.interval}
          onChange={(event) =>
            change({
              ...value,
              interval: event.target.value as Subscription["interval"],
            })
          }
        >
          <option value="monthly">Месяц</option>
          <option value="half_year">Полгода</option>
          <option value="yearly">Год</option>
        </select>
      </label>
      <label>
        Стоимость в копейках RUB
        <input
          type="number"
          min={0}
          max={1000000000000}
          step={1}
          required
          value={value.price_minor}
          onChange={(event) =>
            change({ ...value, price_minor: Number(event.target.value) })
          }
        />
      </label>
      {(
        [
          ["trial_ends_at", "Конец пробного периода (UTC)"],
          ["period_start", "Начало периода (UTC)"],
          ["period_end", "Конец периода (UTC)"],
        ] as const
      ).map(([field, label]) => (
        <label key={field}>
          {label}
          <input
            type="date"
            value={value[field]?.slice(0, 10) || ""}
            required={field === "trial_ends_at" && value.status === "trial"}
            onChange={(event) =>
              change({
                ...value,
                [field]: event.target.value
                  ? `${event.target.value}T00:00:00Z`
                  : null,
              })
            }
          />
        </label>
      ))}
    </div>
  );
}

function CreateGarden({ enabled }: { enabled: boolean }) {
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("Europe/Moscow");
  const [operatingProfile, setOperatingProfile] = useState<"KINDERGARTEN" | "GYMNASTICS">("KINDERGARTEN");
  const [username, setUsername] = useState("");
  const [subscription, setSubscription] =
    useState<Subscription>(initialSubscription);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Provisioning | null>(null);
  const terms = organizationTerms(operatingProfile);
  const key = useRef(crypto.randomUUID());
  const fingerprint = useRef("");
  const [attempted, setAttempted] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!enabled || !confirmed || busyRef.current) return;
    const input = {
      name,
      timezone,
      operating_profile: operatingProfile,
      director_username: username,
      credential_handoff_confirmed: true as const,
      subscription,
    };
    const nextFingerprint = JSON.stringify(input);
    if (fingerprint.current && fingerprint.current !== nextFingerprint) {
      setError(
        "Повторите запрос с исходными данными или начните новую регистрацию.",
      );
      return;
    }
    fingerprint.current = nextFingerprint;
    setAttempted(true);
    busyRef.current = true;
    setBusy(true);
    setError("");
    try {
      setResult(
        await platformApi.provision({
          ...input,
          idempotency_key: key.current,
        } satisfies CreateOrganization),
      );
    } catch (reason) {
      setError(message(reason));
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }
  function reset() {
    key.current = crypto.randomUUID();
    fingerprint.current = "";
    setAttempted(false);
    setResult(null);
    setError("");
    setName("");
    setUsername("");
    setConfirmed(false);
  }
  return (
    <section className="platform-panel">
      <h2>Регистрация организации</h2>
      {!enabled && (
        <p role="alert">
          Защищённая передача одноразовых учётных данных не настроена.
          Регистрация отключена.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
      {result ? (
        <div>
          <h3>{organizationTerms(result.organization.operating_profile).registrationSuccess}</h3>
          <Link href={`/platform/organizations/${result.organization.id}`}>
            {result.organization.name}
          </Link>
          {result.temporary_password ? (
            <>
              <p>
                Одноразовый пароль. Передайте директору только по утверждённому
                защищённому каналу. После закрытия он недоступен; не включайте
                его в скриншоты.
              </p>
              <label>
                Одноразовый пароль директора
                <input
                  type="password"
                  readOnly
                  autoComplete="off"
                  value={result.temporary_password}
                />
              </label>
              <button
                className="button secondary"
                onClick={() =>
                  setResult({ ...result, temporary_password: undefined })
                }
              >
                Пароль передан — скрыть
              </button>
            </>
          ) : (
            <p>Повтор запроса: пароль повторно не выдаётся.</p>
          )}
          <button className="button secondary" onClick={reset}>
            Новая регистрация
          </button>
        </div>
      ) : (
        <form
          className="platform-form"
          onSubmit={(event) => void submit(event)}
        >
          <label>
            {`Название ${terms.organizationGenitive}`}
            <input
              required
              maxLength={200}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>Профиль работы
            <select value={operatingProfile} onChange={event => setOperatingProfile(event.target.value as "KINDERGARTEN" | "GYMNASTICS")}>
              <option value="KINDERGARTEN">Детский сад</option>
              <option value="GYMNASTICS">Спортивная секция (гимнастика)</option>
            </select>
          </label>
          <label>
            Часовой пояс
            <input
              required
              maxLength={64}
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
            />
          </label>
          <label>
            Логин первого директора
            <input
              required
              minLength={3}
              maxLength={64}
              pattern="[a-zA-Z0-9][a-zA-Z0-9_-]{2,63}"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>
          <SubscriptionFields value={subscription} change={setSubscription} />
          <label>
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            Подтверждаю защищённую передачу одноразового пароля
          </label>
          <button className="button" disabled={!enabled || !confirmed || busy}>
            Создать организацию
          </button>
          {attempted && (
            <button
              type="button"
              className="button secondary"
              disabled={busy}
              onClick={reset}
            >
              Начать новую регистрацию
            </button>
          )}
        </form>
      )}
    </section>
  );
}

function GardenDetail({
  garden,
  onChanged,
}: {
  garden: PlatformOrganization;
  onChanged: () => void;
}) {
  const terms = organizationTerms(garden.operating_profile);
  const [confirmation, setConfirmation] = useState("");
  const [profileDraft, setProfileDraft] = useState<PlatformOrganization["operating_profile"]>(garden.operating_profile);
  const [reason, setReason] = useState("owner_request");
  const [subscription, setSubscription] = useState<Subscription>(
    garden.subscription || initialSubscription(),
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  async function action(kind: "lifecycle" | "subscription" | "profile") {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    try {
      if (kind === "lifecycle")
        await platformApi.lifecycle(
          garden.id,
          garden.status !== "blocked",
          confirmation,
          reason,
        );
      else if (kind === "subscription")
        await platformApi.subscription(garden.id, confirmation, subscription);
      else await platformApi.changeProfile(garden.id, confirmation, profileDraft);
      onChanged();
    } catch (error) {
      setError(message(error));
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }
  return (
    <section className="platform-panel">
      <h2>{garden.name}</h2>
      <p>
        {statuses[garden.status]} · {garden.timezone} · {garden.operating_profile === "GYMNASTICS" ? "Спортивная секция" : "Детский сад"}
      </p>
      <p>{onboarding[garden.onboarding_status]}</p>
      {error && <p role="alert">{error}</p>}
      <div className="platform-form">
        <label>
          {`Введите название ${terms.organizationGenitive} для подтверждения`}
          <input
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
          />
        </label>
        <label>Профиль организации
          <select value={profileDraft} onChange={event => setProfileDraft(event.target.value as "KINDERGARTEN" | "GYMNASTICS")}>
            <option value="KINDERGARTEN">Детский сад</option>
            <option value="GYMNASTICS">Спортивная секция (гимнастика)</option>
          </select>
        </label>
        <button className="button secondary" disabled={busy || confirmation !== garden.name || profileDraft === garden.operating_profile} onClick={() => void action("profile")}>Изменить профиль</button>
        <label>
          Причина
          <select
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          >
            <option value="owner_request">Решение владельца</option>
            <option value="security">Безопасность</option>
            <option value="administrative">Административная</option>
          </select>
        </label>
        <button
          className="button secondary"
          disabled={
            busy || confirmation !== garden.name || garden.status === "archived"
          }
          onClick={() => void action("lifecycle")}
        >
          {garden.status === "blocked"
          ? `Разблокировать ${terms.organization}`
            : `Заблокировать ${terms.organization}`}
        </button>
        <h3>Подписка · Стандартный план</h3>
        <p>{`Статус оплаты не блокирует ${terms.organization} автоматически.`}</p>
        <SubscriptionFields value={subscription} change={setSubscription} />
        <button
          className="button"
          disabled={busy || confirmation !== garden.name}
          onClick={() => void action("subscription")}
        >
          Сохранить подписку
        </button>
      </div>
    </section>
  );
}
