/* RegimeForge Alpha - Dashboard JavaScript */
var orderType = "market",
  sizeUnit = "usdt",
  coinPrice = 0,
  aiSignal = null,
  aiData = null,
  currentCoin = "BTC";
var coinStepSizes = {
  BTC: 3,
  ETH: 3,
  SOL: 2,
  XRP: 1,
  BNB: 3,
  ADA: 1,
  DOGE: 0,
  LTC: 3,
};

function getStepDecimals() {
  return coinStepSizes[currentCoin] || 4;
}
function roundToStep(val) {
  var d = getStepDecimals();
  return Math.floor(val * Math.pow(10, d)) / Math.pow(10, d);
}

function changeCoin(coin) {
  currentCoin = coin;
  showMsg("Switching to " + coin + "/USDT...", "info");
  post("/api/coin", { coin: coin }, function (r) {
    if (r.success) {
      document.getElementById("current-coin").textContent = coin;
      document.getElementById("market-coin").textContent = coin;
      document.getElementById("position-coin").textContent = coin;
      document.getElementById("coin-unit-btn").textContent = coin;
      ai_engine_reset();
      loadTPSettings();
      refreshData();
      showMsg("Now trading " + coin + "/USDT", "success");
    } else {
      showMsg("Error: " + (r.error || "Failed to switch coin"), "error");
      document.getElementById("coin-select").value = currentCoin;
    }
  });
}

function ai_engine_reset() {
  document.getElementById("ai-signal").textContent = "...";
  document.getElementById("ai-confidence").textContent = "--";
  document.getElementById("ai-regime").innerHTML =
    "<span class='regime-badge regime-range'>Analyzing...</span>";
}

function setOrderType(t) {
  orderType = t;
  document.getElementById("market-btn").className =
    t === "market" ? "toggle-btn active" : "toggle-btn";
  document.getElementById("limit-btn").className =
    t === "limit" ? "toggle-btn active" : "toggle-btn";
  document.getElementById("limit-section").className =
    t === "limit" ? "limit-section show" : "limit-section";
  if (t === "limit" && coinPrice > 0)
    document.getElementById("limit-price").value = coinPrice.toFixed(2);
}

function setSizeUnit(u) {
  var oldUnit = sizeUnit,
    sizeInput = document.getElementById("trade-size"),
    oldVal = parseFloat(sizeInput.value) || 0;
  sizeUnit = u;
  document.getElementById("coin-unit-btn").className =
    u === "coin" ? "size-unit-btn active" : "size-unit-btn";
  document.getElementById("usdt-btn").className =
    u === "usdt" ? "size-unit-btn active" : "size-unit-btn";
  var d = getStepDecimals();
  if (coinPrice > 0 && oldVal > 0) {
    if (oldUnit === "usdt" && u === "coin") {
      sizeInput.value = roundToStep(oldVal / coinPrice).toFixed(d);
      sizeInput.step = Math.pow(10, -d).toString();
    } else if (oldUnit === "coin" && u === "usdt") {
      sizeInput.value = Math.round(oldVal * coinPrice);
      sizeInput.step = "1";
    }
  }
  updateSizeHint();
}

function updateSizeHint() {
  var size = parseFloat(document.getElementById("trade-size").value) || 0,
    hint = document.getElementById("size-hint");
  var d = getStepDecimals();
  if (coinPrice > 0 && size > 0) {
    hint.textContent =
      sizeUnit === "usdt"
        ? "≈ " + roundToStep(size / coinPrice).toFixed(d) + " " + currentCoin
        : "≈ $" + (size * coinPrice).toFixed(2) + " USDT";
  } else hint.textContent = "";
}

function showMsg(txt, type) {
  var m = document.getElementById("message");
  m.innerHTML = "<div class='alert alert-" + type + "'>" + txt + "</div>";
  setTimeout(function () {
    m.innerHTML = "";
  }, 5000);
}

function get(url, cb) {
  var x = new XMLHttpRequest();
  x.open("GET", url, true);
  x.onload = function () {
    try {
      cb(JSON.parse(x.responseText));
    } catch (e) {
      cb({ error: "Invalid response" });
    }
  };
  x.onerror = function () {
    cb({ error: "Network error" });
  };
  x.send();
}

function post(url, data, cb) {
  var x = new XMLHttpRequest();
  x.open("POST", url, true);
  x.setRequestHeader("Content-Type", "application/json");
  x.onload = function () {
    try {
      cb(JSON.parse(x.responseText));
    } catch (e) {
      cb({ error: "Invalid response: " + x.responseText });
    }
  };
  x.onerror = function () {
    cb({ error: "Network error" });
  };
  x.send(JSON.stringify(data));
}

function updateAIDisplay(data) {
  if (!data || data.error) return;
  aiSignal = data.signal;
  aiData = data;
  var regimeEl = document.getElementById("ai-regime");
  var regimeClass =
    {
      BULL_TRENDING: "regime-bull",
      BEAR_TRENDING: "regime-bear",
      RANGE_BOUND: "regime-range",
      HIGH_VOLATILITY: "regime-highvol",
      LOW_VOLATILITY: "regime-lowvol",
    }[data.regime] || "regime-range";
  regimeEl.innerHTML =
    "<span class='regime-badge " +
    regimeClass +
    "'>" +
    data.regime.replace(/_/g, " ") +
    "</span>";
  var signalDisplay = document.getElementById("ai-signal-display");
  var signalClass =
    { LONG: "signal-long", SHORT: "signal-short", NEUTRAL: "signal-neutral" }[
      data.signal
    ] || "signal-neutral";
  signalDisplay.className = "signal-display " + signalClass;
  document.getElementById("ai-signal").textContent = data.signal;
  document.getElementById("ai-confidence").textContent = Math.round(
    data.confidence * 100,
  );
  var confBar = document.getElementById("confidence-bar");
  confBar.style.width = data.confidence * 100 + "%";
  confBar.style.background =
    data.signal === "LONG"
      ? "#00ff88"
      : data.signal === "SHORT"
        ? "#ff4466"
        : "#ffaa00";
  var ind = data.indicators || {};
  document.getElementById("ind-rsi").textContent =
    ind.rsi !== undefined ? ind.rsi.toFixed(1) + "%" : "--";
  document.getElementById("ind-trend").textContent =
    ind.trend_strength !== undefined ? ind.trend_strength.toFixed(2) : "--";
  document.getElementById("ind-vol").textContent =
    ind.volatility_pct !== undefined
      ? ind.volatility_pct.toFixed(1) + "%"
      : "--";
  document.getElementById("ind-change").textContent =
    ind.price_change_24h !== undefined
      ? (ind.price_change_24h >= 0 ? "+" : "") +
        ind.price_change_24h.toFixed(2) +
        "%"
      : "--";
  var reasoningEl = document.getElementById("ai-reasoning");
  if (data.reasoning && data.reasoning.length > 0) {
    reasoningEl.innerHTML = data.reasoning
      .map(function (r) {
        return "<div class='reasoning-item'>" + r + "</div>";
      })
      .join("");
  }
}

function runAIAnalysis() {
  document.getElementById("ai-signal").textContent = "...";
  get("/api/ai/analyze", function (d) {
    if (d.error) {
      showMsg("AI Error: " + d.error, "error");
      return;
    }
    updateAIDisplay(d);
  });
}

function updateAISizeHint() {
  var el = document.getElementById("ai-trade-size");
  if (!el) return;
  var usdtSize = parseFloat(el.value);
  if (isNaN(usdtSize) || usdtSize <= 0) usdtSize = 10;
  var hint = document.getElementById("ai-size-hint");
  var d = getStepDecimals();
  if (hint && coinPrice > 0) {
    hint.textContent =
      "≈ " + roundToStep(usdtSize / coinPrice).toFixed(d) + " " + currentCoin;
  }
}

function executeAITrade(direction) {
  var el = document.getElementById("ai-trade-size");
  if (!el) {
    showMsg("AI trade size input not found", "error");
    return;
  }
  var usdtSize = parseFloat(el.value);
  if (isNaN(usdtSize) || usdtSize <= 0) {
    showMsg("Enter a valid trade size", "error");
    return;
  }
  if (usdtSize < 5) {
    showMsg("Minimum AI trade size is $5", "error");
    return;
  }
  if (coinPrice <= 0) {
    showMsg("Price not loaded yet, please wait", "error");
    return;
  }
  var d = getStepDecimals();
  var coinSize = roundToStep(usdtSize / coinPrice).toFixed(d);
  if (parseFloat(coinSize) <= 0) {
    showMsg("Trade size too small for " + currentCoin, "error");
    return;
  }
  if (
    !confirm(
      "Execute AI " +
        direction.toUpperCase() +
        " " +
        coinSize +
        " " +
        currentCoin +
        " (~$" +
        usdtSize +
        ")?",
    )
  )
    return;
  document.getElementById("ai-" + direction + "-btn").disabled = true;
  post("/api/ai/trade", { direction: direction, size: coinSize }, function (r) {
    document.getElementById("ai-" + direction + "-btn").disabled = false;
    if (r.success) {
      showMsg("AI Trade executed! Order: " + r.order_id, "success");
      document.getElementById("ai-log-status").className =
        "ai-log-status ai-log-success";
      document.getElementById("ai-log-status").textContent =
        "✓ AI log submitted for order " + r.order_id;
      refreshData();
    } else {
      var errMsg = r.error || r.message || "Trade failed";
      if (typeof errMsg === "object") errMsg = JSON.stringify(errMsg);
      showMsg("Error: " + errMsg, "error");
    }
  });
}

function refreshData() {
  get("/api/price", function (d) {
    if (d.error) {
      console.log("Price error:", d.error);
      return;
    }
    if (d.price) {
      coinPrice = parseFloat(d.price);
      document.getElementById("btc-price").textContent =
        coinPrice.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
      if (d.high_24h)
        document.getElementById("high-24h").textContent = parseFloat(
          d.high_24h,
        ).toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
      if (d.low_24h)
        document.getElementById("low-24h").textContent = parseFloat(
          d.low_24h,
        ).toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
      if (d.change_24h !== undefined) {
        var ch = parseFloat(d.change_24h);
        var chEl = document.getElementById("price-change");
        chEl.textContent = (ch >= 0 ? "+" : "") + ch.toFixed(2) + "%";
        chEl.className = "price-change " + (ch >= 0 ? "positive" : "negative");
      }
      updateSizeHint();
      updateAISizeHint();
    }
  });
  get("/api/balance", function (d) {
    if (d.balance)
      document.getElementById("balance").textContent = parseFloat(
        d.balance,
      ).toFixed(2);
  });
  get("/api/position", function (d) {
    updatePos(d);
  });
  get("/api/orders", function (d) {
    updateOrders(d);
  });
  get("/api/history", function (d) {
    updateHistory(d);
  });
  get("/api/ai/analyze", function (d) {
    if (!d.error) updateAIDisplay(d);
  });
  loadAllPositions();
  document.getElementById("last-update").textContent =
    new Date().toLocaleTimeString();
}

var currentPosition = null;
function updatePos(d) {
  var c = document.getElementById("position-info"),
    b = document.getElementById("close-btn");
  if (d.position && parseFloat(d.position.size) > 0) {
    currentPosition = d.position;
    var p = d.position,
      size = parseFloat(p.size) || 0,
      entry = parseFloat(p.avg_price) || 0,
      liq = parseFloat(p.liquidation_price) || 0,
      lev = parseInt(p.leverage) || 20;
    var pnl = 0;
    if (coinPrice > 0 && entry > 0 && size > 0) {
      pnl = (coinPrice - entry) * size * (p.side === "LONG" ? 1 : -1);
    }
    var pc = pnl >= 0 ? "positive" : "negative",
      sc = p.side === "LONG" ? "positive" : "negative";
    var usdtValue = coinPrice > 0 ? (size * coinPrice).toFixed(2) : "--";
    var margin = coinPrice > 0 ? ((size * coinPrice) / lev).toFixed(2) : "--";
    c.innerHTML =
      "<div class='stat'><span class='stat-label'>Side</span><span class='stat-value " +
      sc +
      "'>" +
      p.side +
      " <span style='color:#00d4ff;font-size:12px'>" +
      lev +
      "x</span></span></div>" +
      "<div class='stat'><span class='stat-label'>Size</span><span class='stat-value'>" +
      p.size +
      " " +
      currentCoin +
      " <span style='color:#888;font-size:12px'>($" +
      usdtValue +
      ")</span></span></div>" +
      "<div class='stat'><span class='stat-label'>Margin</span><span class='stat-value'>$" +
      margin +
      "</span></div>" +
      "<div class='stat'><span class='stat-label'>Entry</span><span class='stat-value'>$" +
      entry.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }) +
      "</span></div>" +
      "<div class='stat'><span class='stat-label'>Liq Price</span><span class='stat-value negative'>$" +
      (liq > 0
        ? liq.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })
        : "--") +
      "</span></div>" +
      "<div class='stat'><span class='stat-label'>P/L</span><span class='stat-value " +
      pc +
      "'>$" +
      pnl.toFixed(2) +
      "</span></div>";
    b.disabled = false;
  } else {
    currentPosition = null;
    c.innerHTML =
      "<div class='no-position'>No open " + currentCoin + " position</div>";
    b.disabled = true;
  }
}

function updateOrders(d) {
  var c = document.getElementById("open-orders");
  if (d.orders && d.orders.length > 0) {
    var h = "";
    for (var i = 0; i < d.orders.length; i++) {
      var o = d.orders[i],
        side = o.side || o.type || "ORDER",
        tc =
          side.toLowerCase().indexOf("long") >= 0 || side === "1"
            ? "positive"
            : "negative";
      var displaySide =
        side === "1" ? "LONG" : side === "2" ? "SHORT" : side.toUpperCase();
      h +=
        "<div class='order-item'><div><span class='" +
        tc +
        "'>" +
        displaySide +
        "</span> " +
        (o.size || o.amount) +
        " @ $" +
        parseFloat(o.price || 0).toLocaleString() +
        "</div><button class='order-cancel-btn' data-id='" +
        (o.order_id || o.orderId) +
        "'>Cancel</button></div>";
    }
    c.innerHTML = h;
    c.querySelectorAll(".order-cancel-btn").forEach(function (btn) {
      btn.onclick = function () {
        cancelOrder(this.getAttribute("data-id"));
      };
    });
  } else c.innerHTML = "<div class='no-position'>No open orders</div>";
}

function updateHistory(d) {
  var c = document.getElementById("trade-history");
  if (d.trades && d.trades.length > 0) {
    var h = "",
      tr = d.trades.slice(0, 8);
    for (var i = 0; i < tr.length; i++) {
      var t = tr[i],
        side = t.side || t.type || "TRADE",
        tc =
          side.toLowerCase().indexOf("long") >= 0 ||
          side === "1" ||
          side === "3"
            ? "positive"
            : "negative";
      var displaySide =
        side === "1"
          ? "OPEN LONG"
          : side === "2"
            ? "OPEN SHORT"
            : side === "3"
              ? "CLOSE LONG"
              : side === "4"
                ? "CLOSE SHORT"
                : side.toUpperCase();
      h +=
        "<div class='trade-item'><span class='" +
        tc +
        "'>" +
        displaySide +
        "</span> " +
        (t.size || t.amount) +
        " " +
        currentCoin +
        " @ $" +
        parseFloat(t.price_avg || t.price || 0).toLocaleString() +
        "</div>";
    }
    c.innerHTML = h;
  } else c.innerHTML = "<div class='no-position'>No recent trades</div>";
}

function loadAllPositions() {
  get("/api/all_positions", function (d) {
    var c = document.getElementById("all-positions");
    if (d.positions && d.positions.length > 0) {
      var h = "";
      for (var i = 0; i < d.positions.length; i++) {
        var p = d.positions[i];
        var sideClass = p.side === "LONG" ? "positive" : "negative";
        var pnlClass = p.pnl_pct >= 0 ? "positive" : "negative";
        var pnlSign = p.pnl_pct >= 0 ? "+" : "";
        h +=
          "<div class='stat' style='padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.1)'>";
        h +=
          "<div style='display:flex;justify-content:space-between;align-items:center;width:100%'>";
        h +=
          "<div><span style='font-weight:600;color:#00d4ff'>" +
          p.coin +
          "</span> <span class='" +
          sideClass +
          "'>" +
          p.side +
          "</span> <span style='color:#888;font-size:11px'>" +
          p.leverage +
          "x</span></div>";
        h +=
          "<div style='text-align:right'><span class='" +
          pnlClass +
          "'>" +
          pnlSign +
          p.pnl_pct +
          "%</span> <span style='color:#888;font-size:11px'>($" +
          p.pnl_usdt +
          ")</span></div>";
        h +=
          "</div><div style='display:flex;justify-content:space-between;font-size:11px;color:#888;margin-top:4px;width:100%'>";
        h +=
          "<span>" +
          p.size +
          " @ $" +
          p.entry_price.toLocaleString(undefined, {
            maximumFractionDigits: 2,
          }) +
          "</span>";
        h += "<span>Value: $" + p.value_usdt + "</span></div></div>";
      }
      c.innerHTML = h;
    } else {
      c.innerHTML = "<div class='no-position'>No open positions</div>";
    }
  });
}

function cancelOrder(id) {
  if (!id) {
    showMsg("Invalid order ID", "error");
    return;
  }
  if (!confirm("Cancel order " + id + "?")) return;
  post("/api/cancel", { orderId: id }, function (r) {
    if (r.success) {
      showMsg("Order cancelled", "success");
      refreshData();
    } else showMsg("Error: " + (r.error || "Failed to cancel"), "error");
  });
}

function openTrade(side) {
  var sizeVal = parseFloat(document.getElementById("trade-size").value),
    price = document.getElementById("limit-price").value;
  if (!sizeVal || sizeVal <= 0) {
    showMsg("Enter valid size", "error");
    return;
  }
  if (orderType === "limit" && (!price || parseFloat(price) <= 0)) {
    showMsg("Enter limit price", "error");
    return;
  }
  if (coinPrice <= 0) {
    showMsg("Price not loaded yet", "error");
    return;
  }
  var d = getStepDecimals();
  var coinSize =
    sizeUnit === "usdt"
      ? roundToStep(sizeVal / coinPrice).toFixed(d)
      : roundToStep(sizeVal).toFixed(d);
  if (parseFloat(coinSize) <= 0) {
    showMsg("Size too small for " + currentCoin, "error");
    return;
  }
  if (!confirm(side.toUpperCase() + " " + coinSize + " " + currentCoin + "?"))
    return;
  post(
    "/api/open",
    {
      side: side,
      size: coinSize,
      order_type: orderType,
      price: orderType === "limit" ? price : null,
    },
    function (r) {
      if (r.success) {
        showMsg("Order placed! ID: " + r.order_id, "success");
        refreshData();
      } else {
        var errMsg = r.error || "Failed";
        if (typeof errMsg === "object") errMsg = JSON.stringify(errMsg);
        showMsg("Error: " + errMsg, "error");
      }
    },
  );
}

function closePosition() {
  if (!confirm("Close " + currentCoin + " position at market?")) return;
  post("/api/close", {}, function (r) {
    if (r.success) {
      showMsg("Position closed! ID: " + r.order_id, "success");
      post("/api/takeprofit/reset", {}, function () {});
      refreshData();
    } else showMsg("Error: " + (r.error || "Failed"), "error");
  });
}

// Take-Profit Functions
var tpEnabled = false,
  tpMode = "fixed";

function toggleTP() {
  tpEnabled = document.getElementById("tp-enabled").checked;
  document.getElementById("tp-controls").style.display = tpEnabled
    ? "block"
    : "none";
  saveTPSettings();
}

function setTPMode(mode) {
  tpMode = mode;
  document.getElementById("tp-fixed-btn").className =
    mode === "fixed" ? "toggle-btn active" : "toggle-btn";
  document.getElementById("tp-trailing-btn").className =
    mode === "trailing" ? "toggle-btn active" : "toggle-btn";
  document.getElementById("tp-fixed-settings").style.display =
    mode === "fixed" ? "block" : "none";
  document.getElementById("tp-trailing-settings").style.display =
    mode === "trailing" ? "block" : "none";
  saveTPSettings();
}

function saveTPSettings() {
  var settings = {
    enabled: tpEnabled,
    mode: tpMode,
    fixed_target_pct:
      parseFloat(document.getElementById("tp-fixed-pct").value) || 1.5,
    trailing_drop_pct:
      parseFloat(document.getElementById("tp-trailing-pct").value) || 0.5,
  };
  post("/api/takeprofit/settings", settings, function (r) {});
}

function checkTakeProfit() {
  if (!tpEnabled) return;
  get("/api/takeprofit/check", function (d) {
    var statusEl = document.getElementById("tp-status");
    if (!statusEl) return;
    if (d.reason) {
      var color = d.should_close ? "#00ff88" : "#888";
      var icon = d.should_close ? "🎯" : "📊";
      statusEl.innerHTML = icon + " " + d.reason;
      statusEl.style.color = color;
      if (d.profit_pct !== undefined) {
        var profitColor = d.profit_pct >= 0 ? "#00ff88" : "#ff4466";
        statusEl.innerHTML +=
          "<br><span style='color:" +
          profitColor +
          "'>P/L: " +
          (d.profit_pct >= 0 ? "+" : "") +
          d.profit_pct.toFixed(2) +
          "%</span>";
        if (d.peak_profit_pct > 0) {
          statusEl.innerHTML +=
            " | Peak: +" + d.peak_profit_pct.toFixed(2) + "%";
        }
      }
      if (d.should_close) {
        statusEl.style.background = "rgba(0,255,136,0.15)";
        statusEl.style.border = "1px solid rgba(0,255,136,0.3)";
        statusEl.innerHTML =
          "<span style='color:#00ff88;font-weight:bold'>🎯 CLOSING...</span>";
        closePositionAuto();
      } else {
        statusEl.style.background = "rgba(0,0,0,0.2)";
        statusEl.style.border = "none";
      }
    } else {
      statusEl.innerHTML = "Waiting for position...";
      statusEl.style.color = "#888";
    }
  });
}

function closePositionAuto() {
  post("/api/close", {}, function (r) {
    if (r.success) {
      showMsg("🎯 Take-Profit executed! Order: " + r.order_id, "success");
      post("/api/takeprofit/reset", {}, function () {});
      refreshData();
    } else {
      showMsg("Error closing: " + (r.error || "Failed"), "error");
    }
  });
}

function loadTPSettings() {
  get("/api/takeprofit/settings", function (d) {
    if (d.enabled !== undefined) {
      tpEnabled = d.enabled;
      tpMode = d.mode || "fixed";
      document.getElementById("tp-enabled").checked = tpEnabled;
      document.getElementById("tp-controls").style.display = tpEnabled
        ? "block"
        : "none";
      document.getElementById("tp-fixed-pct").value = d.fixed_target_pct || 1.5;
      document.getElementById("tp-trailing-pct").value =
        d.trailing_drop_pct || 0.5;
      setTPMode(tpMode);
    }
  });
}

// Full Automation Functions
var autoEnabled = false;

function toggleAutomation() {
  autoEnabled = document.getElementById("auto-master").checked;
  document.getElementById("auto-controls").style.display = autoEnabled
    ? "block"
    : "none";
  document.getElementById("auto-master-label").textContent = autoEnabled
    ? "ON"
    : "OFF";
  document.getElementById("auto-master-label").style.color = autoEnabled
    ? "#00ff88"
    : "#888";
  saveAutoSettings();
}

function updatePositionValue() {
  var margin = parseFloat(document.getElementById("auto-margin").value) || 30;
  var leverage = parseInt(document.getElementById("auto-leverage").value) || 20;
  document.getElementById("auto-position-value").textContent =
    "$" + margin * leverage;
}

function saveAutoSettings() {
  updatePositionValue();
  var settings = {
    enabled: document.getElementById("auto-master").checked,
    auto_entry: document.getElementById("auto-entry").checked,
    auto_take_profit: document.getElementById("auto-tp").checked,
    auto_stop_loss: document.getElementById("auto-sl").checked,
    margin_usdt: parseFloat(document.getElementById("auto-margin").value) || 30,
    leverage: parseInt(document.getElementById("auto-leverage").value) || 20,
    min_confidence:
      (parseFloat(document.getElementById("auto-min-conf").value) || 65) / 100,
    stop_loss_pct:
      parseFloat(document.getElementById("auto-sl-pct").value) || 2,
    cooldown_minutes:
      parseInt(document.getElementById("auto-cooldown").value) || 5,
    max_trades_per_hour:
      parseInt(document.getElementById("auto-max-trades").value) || 3,
    daily_loss_limit_usdt:
      parseFloat(document.getElementById("auto-daily-limit").value) || 20,
  };
  post("/api/automation/settings", settings, function (r) {
    if (r.success) {
      updateAutoStatus("Settings saved");
    }
  });
}

function loadAutoSettings() {
  get("/api/automation/settings", function (d) {
    if (d.enabled !== undefined) {
      autoEnabled = d.enabled;
      document.getElementById("auto-master").checked = autoEnabled;
      document.getElementById("auto-controls").style.display = autoEnabled
        ? "block"
        : "none";
      document.getElementById("auto-master-label").textContent = autoEnabled
        ? "ON"
        : "OFF";
      document.getElementById("auto-master-label").style.color = autoEnabled
        ? "#00ff88"
        : "#888";
      document.getElementById("auto-entry").checked = d.auto_entry || false;
      document.getElementById("auto-tp").checked = d.auto_take_profit || false;
      document.getElementById("auto-sl").checked = d.auto_stop_loss || false;
      document.getElementById("auto-margin").value = d.margin_usdt || 30;
      document.getElementById("auto-leverage").value = d.leverage || 20;
      document.getElementById("auto-min-conf").value = Math.round(
        (d.min_confidence || 0.65) * 100,
      );
      document.getElementById("auto-sl-pct").value = d.stop_loss_pct || 2;
      document.getElementById("auto-cooldown").value = d.cooldown_minutes || 5;
      document.getElementById("auto-max-trades").value =
        d.max_trades_per_hour || 3;
      document.getElementById("auto-daily-limit").value =
        d.daily_loss_limit_usdt || 20;
      updatePositionValue();
    }
  });
}

function updateAutoStatus(msg) {
  var el = document.getElementById("auto-status");
  if (el) el.textContent = msg;
}

function runAutomation() {
  if (!autoEnabled) return;
  get("/api/automation/run", function (d) {
    if (d.action && d.action !== "none") {
      var statusEl = document.getElementById("auto-status");
      if (statusEl) {
        var color = d.action.includes("OPEN")
          ? "#00d4ff"
          : d.action.includes("CLOSE")
            ? "#ffaa00"
            : "#888";
        statusEl.innerHTML =
          "<span style='color:" + color + "'>" + d.action + "</span>";
        if (d.reason)
          statusEl.innerHTML +=
            "<br><span style='color:#666;font-size:10px'>" +
            d.reason +
            "</span>";
      }
      if (d.trade_executed) {
        showMsg("🤖 Auto: " + d.action, "success");
        refreshData();
      }
    } else if (d.reason) {
      updateAutoStatus(d.reason);
    }
  });
}

// Initialize
function initPage() {
  get("/api/coins", function (d) {
    if (d.current) {
      currentCoin = d.current;
      document.getElementById("coin-select").value = currentCoin;
      document.getElementById("current-coin").textContent = currentCoin;
      document.getElementById("market-coin").textContent = currentCoin;
      document.getElementById("position-coin").textContent = currentCoin;
      document.getElementById("coin-unit-btn").textContent = currentCoin;
    }
  });
  loadTPSettings();
  loadAutoSettings();
  loadAllPositions();
  refreshData();
}

document.getElementById("trade-size").addEventListener("input", updateSizeHint);
document
  .getElementById("ai-trade-size")
  .addEventListener("input", updateAISizeHint);
document
  .getElementById("tp-fixed-pct")
  .addEventListener("change", saveTPSettings);
document
  .getElementById("tp-trailing-pct")
  .addEventListener("change", saveTPSettings);
setInterval(refreshData, 30000);
setInterval(checkTakeProfit, 10000);
setInterval(runAutomation, 15000);
initPage();
