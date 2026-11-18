(() => {
  // Keep only confirmed requests awaiting an acknowledgement. Each tab can
  // submit a different receipt; resuming an existing entry reuses its exact body.
  let database;
  function open() {
    if (!database) {
      database = new Promise((resolve, reject) => {
        const request = indexedDB.open("finasist-receipt-submissions", 1);
        request.onupgradeneeded = () => {
          request.result.createObjectStore("pending", {keyPath: "key"}).createIndex("owner", "owner");
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      }).catch(error => { database = null; throw error; });
    }
    return database;
  }

  async function access(mode, run) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction("pending", mode);
      const request = run(transaction.objectStore("pending"));
      transaction.oncomplete = () => resolve(request.result);
      transaction.onabort = () => reject(transaction.error || request.error);
    });
  }

  window.App.receiptSubmissions = {
    pending: owner => access("readonly", store => store.index("owner").get(owner)),
    remember: attempt => access("readwrite", store => store.add(attempt)),
    forget: key => access("readwrite", store => store.delete(key)),
  };
})();
