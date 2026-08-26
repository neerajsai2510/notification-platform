import { useEffect, useState } from "react";

function getStatusStyle(status) {
  switch (status) {
    case "DELIVERED":
      return "bg-green-100 text-green-700";

    case "PROCESSING":
      return "bg-blue-100 text-blue-700";

    case "FAILED":
      return "bg-red-100 text-red-700";

    case "PENDING":
      return "bg-yellow-100 text-yellow-700";

    default:
      return "bg-gray-100 text-gray-700";
  }
}

function App() {
  const [notifications, setNotifications] = useState([]);
  const [recipient, setRecipient] = useState("");
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);

  const fetchNotifications = () => {
    fetch("http://localhost:8000/notifications")
      .then((response) => response.json())
      .then((data) => setNotifications(data))
      .catch((error) => {
        console.error("Failed to fetch notifications:", error);
      });
  };

  useEffect(() => {
    fetchNotifications();

    const socket = new WebSocket(
      "ws://localhost:8000/ws/notifications"
    );

    socket.onopen = () => {
      console.log("WebSocket connected");
    };

    socket.onmessage = (event) => {
      const updatedNotification = JSON.parse(event.data);

      setNotifications((currentNotifications) => {
        const existingNotification = currentNotifications.find(
          (notification) =>
            notification.id === updatedNotification.id
        );

        if (existingNotification) {
          return currentNotifications.map((notification) =>
            notification.id === updatedNotification.id
              ? updatedNotification
              : notification
          );
        }

        return [...currentNotifications, updatedNotification];
      });
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected");
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    return () => {
      socket.close();
    };
  }, []);

  const sendNotification = (event) => {
    event.preventDefault();

    if (!recipient.trim() || !message.trim()) {
      return;
    }

    setIsSending(true);

    fetch("http://localhost:8000/notifications", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        recipient,
        message,
      }),
    })
      .then((response) => response.json())
      .then(() => {
        setRecipient("");
        setMessage("");
      })
      .catch((error) => {
        console.error("Failed to send notification:", error);
      })
      .finally(() => {
        setIsSending(false);
      });
  };

  const deliveredCount = notifications.filter(
    (notification) => notification.status === "DELIVERED"
  ).length;

  const processingCount = notifications.filter(
    (notification) => notification.status === "PROCESSING"
  ).length;

  const failedCount = notifications.filter(
    (notification) => notification.status === "FAILED"
  ).length;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">
            Notification Dashboard
          </h1>

          <p className="mt-2 text-slate-500">
            Real-time notification monitoring and delivery tracking.
          </p>
        </div>

        {/* Stats */}
        <div className="mb-8 grid gap-4 md:grid-cols-4">

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">
              Total
            </p>
            <p className="mt-2 text-3xl font-bold">
              {notifications.length}
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">
              Delivered
            </p>
            <p className="mt-2 text-3xl font-bold text-green-600">
              {deliveredCount}
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">
              Processing
            </p>
            <p className="mt-2 text-3xl font-bold text-blue-600">
              {processingCount}
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">
              Failed
            </p>
            <p className="mt-2 text-3xl font-bold text-red-600">
              {failedCount}
            </p>
          </div>

        </div>

        {/* Create notification */}
        <div className="mb-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">

          <h2 className="mb-5 text-lg font-semibold">
            Send Notification
          </h2>

          <form
            onSubmit={sendNotification}
            className="grid gap-4 md:grid-cols-[1fr_2fr_auto]"
          >

            <input
              type="text"
              placeholder="Recipient"
              value={recipient}
              onChange={(event) =>
                setRecipient(event.target.value)
              }
              className="rounded-lg border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />

            <input
              type="text"
              placeholder="Message"
              value={message}
              onChange={(event) =>
                setMessage(event.target.value)
              }
              className="rounded-lg border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />

            <button
              type="submit"
              disabled={isSending}
              className="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSending ? "Sending..." : "Send"}
            </button>

          </form>
        </div>

        {/* Notifications table */}
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">

          <div className="border-b border-slate-200 px-6 py-5">
            <h2 className="text-lg font-semibold">
              Notifications
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Live updates are delivered through WebSockets.
            </p>
          </div>

          {notifications.length === 0 ? (

            <div className="px-6 py-12 text-center">
              <p className="font-medium text-slate-700">
                No notifications yet
              </p>

              <p className="mt-1 text-sm text-slate-500">
                Create your first notification above.
              </p>
            </div>

          ) : (

            <div className="overflow-x-auto">

              <table className="w-full text-left text-sm">

                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">

                  <tr>
                    <th className="px-6 py-4 font-semibold">
                      ID
                    </th>

                    <th className="px-6 py-4 font-semibold">
                      Recipient
                    </th>

                    <th className="px-6 py-4 font-semibold">
                      Message
                    </th>

                    <th className="px-6 py-4 font-semibold">
                      Status
                    </th>

                    <th className="px-6 py-4 font-semibold">
                      Retries
                    </th>
                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-100">

                  {notifications.map((notification) => (

                    <tr
                      key={notification.id}
                      className="transition hover:bg-slate-50"
                    >

                      <td className="px-6 py-4 font-medium">
                        #{notification.id}
                      </td>

                      <td className="px-6 py-4">
                        {notification.recipient}
                      </td>

                      <td className="max-w-md truncate px-6 py-4 text-slate-600">
                        {notification.message}
                      </td>

                      <td className="px-6 py-4">

                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${getStatusStyle(
                            notification.status
                          )}`}
                        >
                          {notification.status}
                        </span>

                      </td>

                      <td className="px-6 py-4 text-slate-600">
                        {notification.retry_count ?? 0}
                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          )}

        </div>

      </div>
    </div>
  );
}

export default App;
