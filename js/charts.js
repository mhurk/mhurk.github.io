(function(){
  // --- binned operational charts (defrost / compressor RPM) ---------------

  var BAR_CARDS = {
    defrostTemp: { id:"card-defrost-temp", file:"data/defrost_vs_temp.json",     xKey:"temp_bin",     color:"var(--weheat)",  xFmt:function(v){ return v+"°"; } },
    defrostRh:   { id:"card-defrost-rh",   file:"data/defrost_vs_humidity.json", xKey:"humidity_bin", color:"var(--battery)", xFmt:function(v){ return v+"%"; } }
  };

  function renderBarStats(card, data, cfg){
    var total = data.reduce(function(s,d){ return s+d.cycles; }, 0);
    var peak = data.reduce(function(a,b){ return b.cycles>a.cycles ? b : a; }, data[0]);
    card.querySelector('[data-stat="total"]').textContent = total;
    card.querySelector('[data-stat="peak-bin"]').textContent = cfg.xFmt(peak[cfg.xKey]);
    card.querySelector('[data-stat="peak-val"]').textContent = peak.cycles;
  }

  function buildBarChart(key, data){
    var cfg = BAR_CARDS[key];
    var card = document.getElementById(cfg.id);
    var wrap = card.querySelector(".chart-wrap");
    var n = data.length;
    var maxVal = Math.max.apply(null, data.map(function(d){ return d.cycles; }));
    if (maxVal <= 0) maxVal = 1;

    var durVals = data.map(function(d){ return d.avg_duration_min; });
    var durMin = Math.min.apply(null, durVals), durMax = Math.max.apply(null, durVals);
    if (durMin === durMax){ durMin -= 1; durMax += 1; }

    var W=600,H=230,PAD_L=30,PAD_R=8,PAD_T=10,PAD_B=22;
    var MAIN_H=130, DUR_GAP=16, DUR_H=40;
    var plotW=W-PAD_L-PAD_R, mainBottom=PAD_T+MAIN_H;
    var durTop=mainBottom+DUR_GAP, durBottom=durTop+DUR_H;
    var bw = plotW/n;

    function barX(i){ return PAD_L + i*bw; }
    function barY(v){ return PAD_T + (1-v/maxVal)*MAIN_H; }
    function durY(v){ return durTop + (1-(v-durMin)/(durMax-durMin))*DUR_H; }

    var svgns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(svgns,"svg");
    svg.setAttribute("viewBox","0 0 "+W+" "+H);
    svg.setAttribute("preserveAspectRatio","none");

    for (var g=0; g<4; g++){
      var frac = g/3;
      var v = maxVal*frac;
      var y = barY(v);
      var line = document.createElementNS(svgns,"line");
      line.setAttribute("class","gline");
      line.setAttribute("x1",PAD_L); line.setAttribute("x2",W-PAD_R);
      line.setAttribute("y1",y); line.setAttribute("y2",y);
      svg.appendChild(line);
      var txt = document.createElementNS(svgns,"text");
      txt.setAttribute("class","gtick");
      txt.setAttribute("x",2); txt.setAttribute("y",y+3);
      txt.textContent = Math.round(v);
      svg.appendChild(txt);
    }

    var tooltip = document.createElement("div");
    tooltip.className = "tooltip";

    // secondary strip: avg defrost duration per bin, own scale, de-emphasised
    var durLabel = document.createElementNS(svgns,"text");
    durLabel.setAttribute("class","gtick");
    durLabel.setAttribute("x",PAD_L); durLabel.setAttribute("y",durTop-5);
    durLabel.textContent = "avg duration (min)";
    svg.appendChild(durLabel);

    var durD = "M"+(barX(0)+bw/2)+","+durY(durVals[0]);
    for (var i=1;i<n;i++){ durD += " L"+(barX(i)+bw/2)+","+durY(durVals[i]); }
    var durPath = document.createElementNS(svgns,"path");
    durPath.setAttribute("d",durD);
    durPath.setAttribute("fill","none");
    durPath.setAttribute("stroke","var(--ink-2)");
    durPath.setAttribute("stroke-width","1.5");
    svg.appendChild(durPath);

    var durTickMax = document.createElementNS(svgns,"text");
    durTickMax.setAttribute("class","gtick");
    durTickMax.setAttribute("x",2); durTickMax.setAttribute("y",durTop+3);
    durTickMax.textContent = durMax.toFixed(1);
    svg.appendChild(durTickMax);

    var durTickMin = document.createElementNS(svgns,"text");
    durTickMin.setAttribute("class","gtick");
    durTickMin.setAttribute("x",2); durTickMin.setAttribute("y",durBottom+3);
    durTickMin.textContent = durMin.toFixed(1);
    svg.appendChild(durTickMin);

    var hoverDurPt = document.createElementNS(svgns,"circle");
    hoverDurPt.setAttribute("class","hoverpt");
    hoverDurPt.setAttribute("r",3);
    hoverDurPt.setAttribute("fill","var(--ink-1)");
    svg.appendChild(hoverDurPt);

    data.forEach(function(d,i){
      var y = barY(d.cycles);
      var rect = document.createElementNS(svgns,"rect");
      rect.setAttribute("class","bar");
      rect.setAttribute("x", barX(i)+bw*0.12);
      rect.setAttribute("y", y);
      rect.setAttribute("width", Math.max(bw*0.76,1));
      rect.setAttribute("height", Math.max(mainBottom-y,0));
      rect.setAttribute("rx",2);
      rect.setAttribute("fill", cfg.color);
      svg.appendChild(rect);

      rect.addEventListener("mouseenter", function(){
        rect.classList.add("bar-hover");
        var rectBox = svg.getBoundingClientRect();
        var scale = rectBox.width / W;
        var px = (barX(i)+bw/2)*scale;
        var py = y*scale;
        tooltip.innerHTML = cfg.xFmt(d[cfg.xKey]) + ' &nbsp;<b>' + d.cycles + '</b> cycles &nbsp;·&nbsp; avg <b>' + d.avg_duration_min.toFixed(1) + '</b> min';
        tooltip.style.left = px+"px";
        tooltip.style.top = (py-8)+"px";
        tooltip.style.opacity = 1;
        hoverDurPt.setAttribute("cx", barX(i)+bw/2);
        hoverDurPt.setAttribute("cy", durY(d.avg_duration_min));
        hoverDurPt.style.opacity = 1;
      });
      rect.addEventListener("mouseleave", function(){
        rect.classList.remove("bar-hover");
        tooltip.style.opacity = 0;
        hoverDurPt.style.opacity = 0;
      });
    });

    [0, Math.round((n-1)/2), n-1].forEach(function(i){
      var txt = document.createElementNS(svgns,"text");
      txt.setAttribute("class","xtick");
      txt.setAttribute("x", barX(i)+bw/2);
      txt.setAttribute("y", H-4);
      txt.setAttribute("text-anchor","middle");
      txt.textContent = cfg.xFmt(data[i][cfg.xKey]);
      svg.appendChild(txt);
    });

    wrap.appendChild(svg);
    wrap.appendChild(tooltip);

    renderBarStats(card, data, cfg);
  }

  function buildRpmChart(data){
    var card = document.getElementById("card-rpm");
    var wrap = card.querySelector(".chart-wrap");
    var n = data.length;
    var vals = data.map(function(d){ return d.rpm; });
    var xs = data.map(function(d){ return d.outdoor_temp; });
    var min = Math.min.apply(null,vals), max = Math.max.apply(null,vals);
    var pad = (max-min)*0.12; min -= pad; max += pad;

    var W=600,H=200,PAD_L=40,PAD_R=8,PAD_T=12,PAD_B=22;
    var plotW=W-PAD_L-PAD_R, plotH=H-PAD_T-PAD_B;
    function X(i){ return PAD_L + (i/(n-1))*plotW; }
    function Y(v){ return PAD_T + (1-(v-min)/(max-min))*plotH; }

    var color = "var(--weheat)";
    var svgns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(svgns,"svg");
    svg.setAttribute("viewBox","0 0 "+W+" "+H);
    svg.setAttribute("preserveAspectRatio","none");

    var defs = document.createElementNS(svgns,"defs");
    var grad = document.createElementNS(svgns,"linearGradient");
    grad.setAttribute("id","grad-rpm");
    grad.setAttribute("x1","0"); grad.setAttribute("y1","0");
    grad.setAttribute("x2","0"); grad.setAttribute("y2","1");
    var s1 = document.createElementNS(svgns,"stop"); s1.setAttribute("offset","0%"); s1.setAttribute("stop-color",color);
    var s2 = document.createElementNS(svgns,"stop"); s2.setAttribute("offset","100%"); s2.setAttribute("stop-color",color); s2.setAttribute("stop-opacity","0");
    grad.appendChild(s1); grad.appendChild(s2);
    defs.appendChild(grad);
    svg.appendChild(defs);

    for (var g=0; g<4; g++){
      var frac = g/3;
      var v = min + frac*(max-min);
      var y = Y(v);
      var line = document.createElementNS(svgns,"line");
      line.setAttribute("class","gline");
      line.setAttribute("x1",PAD_L); line.setAttribute("x2",W-PAD_R);
      line.setAttribute("y1",y); line.setAttribute("y2",y);
      svg.appendChild(line);
      var txt = document.createElementNS(svgns,"text");
      txt.setAttribute("class","gtick");
      txt.setAttribute("x",2); txt.setAttribute("y",y+3);
      txt.textContent = Math.round(v);
      svg.appendChild(txt);
    }

    [0, Math.round((n-1)/2), n-1].forEach(function(i){
      var txt = document.createElementNS(svgns,"text");
      txt.setAttribute("class","xtick");
      txt.setAttribute("x",X(i));
      txt.setAttribute("y",H-4);
      txt.setAttribute("text-anchor", i===0 ? "start" : (i===n-1 ? "end" : "middle"));
      txt.textContent = xs[i]+"°";
      svg.appendChild(txt);
    });

    var d = "M"+X(0)+","+Y(vals[0]);
    for (var i=1;i<n;i++){ d += " L"+X(i)+","+Y(vals[i]); }
    var areaD = d + " L"+X(n-1)+","+(PAD_T+plotH)+" L"+X(0)+","+(PAD_T+plotH)+" Z";
    var area = document.createElementNS(svgns,"path");
    area.setAttribute("class","area");
    area.setAttribute("d",areaD);
    area.setAttribute("fill","url(#grad-rpm)");
    svg.appendChild(area);

    var linePath = document.createElementNS(svgns,"path");
    linePath.setAttribute("class","line-path");
    linePath.setAttribute("d",d);
    linePath.setAttribute("stroke",color);
    svg.appendChild(linePath);

    var hoverLine = document.createElementNS(svgns,"line");
    hoverLine.setAttribute("class","hoverline");
    hoverLine.setAttribute("y1",PAD_T); hoverLine.setAttribute("y2",PAD_T+plotH);
    svg.appendChild(hoverLine);

    var hoverPt = document.createElementNS(svgns,"circle");
    hoverPt.setAttribute("class","hoverpt");
    hoverPt.setAttribute("r",4.5);
    hoverPt.setAttribute("fill",color);
    svg.appendChild(hoverPt);

    var hit = document.createElementNS(svgns,"rect");
    hit.setAttribute("class","hit");
    hit.setAttribute("x",PAD_L); hit.setAttribute("y",0);
    hit.setAttribute("width",plotW); hit.setAttribute("height",H);
    svg.appendChild(hit);

    wrap.appendChild(svg);

    var tooltip = document.createElement("div");
    tooltip.className = "tooltip";
    wrap.appendChild(tooltip);

    function nearestIndex(clientX){
      var rect = svg.getBoundingClientRect();
      var xSvg = ((clientX - rect.left) / rect.width) * W;
      var i = Math.round(((xSvg - PAD_L) / plotW) * (n-1));
      return Math.max(0, Math.min(n-1, i));
    }

    hit.addEventListener("mousemove", function(e){
      var i = nearestIndex(e.clientX);
      var rect = svg.getBoundingClientRect();
      var scale = rect.width / W;
      var px = X(i) * scale;
      var py = Y(vals[i]) * scale;

      hoverLine.setAttribute("x1",X(i)); hoverLine.setAttribute("x2",X(i));
      hoverLine.style.opacity = 1;
      hoverPt.setAttribute("cx",X(i)); hoverPt.setAttribute("cy",Y(vals[i]));
      hoverPt.style.opacity = 1;

      tooltip.innerHTML = xs[i] + '°C &nbsp;<b>' + Math.round(vals[i]) + '</b> RPM <span class="tt-date">(n='+data[i].n+')</span>';
      tooltip.style.left = px+"px";
      tooltip.style.top = (py-10)+"px";
      tooltip.style.opacity = 1;
    });

    hit.addEventListener("mouseleave", function(){
      hoverLine.style.opacity = 0;
      hoverPt.style.opacity = 0;
      tooltip.style.opacity = 0;
    });

    var rawMin = Math.min.apply(null, vals);
    var rawMax = Math.max.apply(null, vals);
    card.querySelector('[data-stat="min"]').textContent = Math.round(rawMin);
    card.querySelector('[data-stat="max"]').textContent = Math.round(rawMax);
    card.querySelector('[data-stat="range"]').textContent = Math.round(rawMax-rawMin);
  }

  function heatColor(count, maxCount){
    var t = maxCount>0 ? count/maxCount : 0;
    var r = Math.round(17 + (88-17)*t);
    var gr = Math.round(20 + (166-20)*t);
    var b = Math.round(23 + (255-23)*t);
    return "rgb("+r+","+gr+","+b+")";
  }

  function buildHeatmap(data){
    var card = document.getElementById("card-defrost-map");
    var wrap = card.querySelector(".chart-wrap");
    var cells = data.cells;

    var tempBins = Array.from(new Set(cells.map(function(c){ return c.temp_bin; }))).sort(function(a,b){ return a-b; });
    var rhBins = Array.from(new Set(cells.map(function(c){ return c.humidity_bin; }))).sort(function(a,b){ return a-b; });
    var cols = tempBins.length, rows = rhBins.length;
    var maxCount = Math.max.apply(null, cells.map(function(c){ return c.count; }));
    if (maxCount <= 0) maxCount = 1;

    var lookup = {};
    cells.forEach(function(c){ lookup[c.temp_bin+"|"+c.humidity_bin] = c.count; });

    var W=600,H=270,PAD_L=34,PAD_R=8,PAD_T=8,GRID_H=176;
    var gridW = W-PAD_L-PAD_R;
    var cellW = gridW/cols, cellH = GRID_H/rows;
    var xLabelY = PAD_T+GRID_H+14;
    var legendY = PAD_T+GRID_H+26;
    var legendW = gridW;

    var svgns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(svgns,"svg");
    svg.setAttribute("viewBox","0 0 "+W+" "+H);
    svg.setAttribute("preserveAspectRatio","none");

    var defs = document.createElementNS(svgns,"defs");
    var legendGrad = document.createElementNS(svgns,"linearGradient");
    legendGrad.setAttribute("id","legend-grad");
    legendGrad.setAttribute("x1","0%"); legendGrad.setAttribute("y1","0%");
    legendGrad.setAttribute("x2","100%"); legendGrad.setAttribute("y2","0%");
    var lg1 = document.createElementNS(svgns,"stop"); lg1.setAttribute("offset","0%"); lg1.setAttribute("stop-color", heatColor(0,maxCount));
    var lg2 = document.createElementNS(svgns,"stop"); lg2.setAttribute("offset","100%"); lg2.setAttribute("stop-color", heatColor(maxCount,maxCount));
    legendGrad.appendChild(lg1); legendGrad.appendChild(lg2);
    defs.appendChild(legendGrad);
    svg.appendChild(defs);

    var tooltip = document.createElement("div");
    tooltip.className = "tooltip";

    tempBins.forEach(function(tb,ci){
      rhBins.forEach(function(rb,ri){
        var count = lookup[tb+"|"+rb] || 0;
        var x = PAD_L+ci*cellW, y = PAD_T+(rows-1-ri)*cellH;
        var rect = document.createElementNS(svgns,"rect");
        rect.setAttribute("x",x); rect.setAttribute("y",y);
        rect.setAttribute("width",cellW); rect.setAttribute("height",cellH);
        rect.setAttribute("fill", heatColor(count,maxCount));
        rect.setAttribute("stroke","var(--bg)");
        rect.setAttribute("stroke-width","1");
        svg.appendChild(rect);

        rect.addEventListener("mouseenter", function(){
          var rectBox = svg.getBoundingClientRect();
          var scale = rectBox.width / W;
          tooltip.innerHTML = tb+'°C / '+rb+'% &nbsp;<b>'+count+'</b> cycles';
          tooltip.style.left = ((x+cellW/2)*scale)+"px";
          tooltip.style.top = (y*scale)+"px";
          tooltip.style.opacity = 1;
          rect.setAttribute("stroke","var(--ink-2)");
        });
        rect.addEventListener("mouseleave", function(){
          tooltip.style.opacity = 0;
          rect.setAttribute("stroke","var(--bg)");
        });
      });
    });

    tempBins.forEach(function(tb,ci){
      if (ci % 4 !== 0 && ci !== tempBins.length-1) return;
      var txt = document.createElementNS(svgns,"text");
      txt.setAttribute("class","xtick");
      txt.setAttribute("x", PAD_L+ci*cellW+cellW/2);
      txt.setAttribute("y", xLabelY);
      txt.setAttribute("text-anchor","middle");
      txt.textContent = tb+"°";
      svg.appendChild(txt);
    });

    rhBins.forEach(function(rb,ri){
      if (ri % 4 !== 0 && ri !== rhBins.length-1) return;
      var txt = document.createElementNS(svgns,"text");
      txt.setAttribute("class","gtick");
      txt.setAttribute("x",2);
      txt.setAttribute("y", PAD_T+(rows-1-ri)*cellH+cellH/2+3);
      txt.textContent = rb+"%";
      svg.appendChild(txt);
    });

    var legendRect = document.createElementNS(svgns,"rect");
    legendRect.setAttribute("x",PAD_L); legendRect.setAttribute("y",legendY);
    legendRect.setAttribute("width",legendW); legendRect.setAttribute("height",8);
    legendRect.setAttribute("fill","url(#legend-grad)");
    svg.appendChild(legendRect);

    var legend0 = document.createElementNS(svgns,"text");
    legend0.setAttribute("class","gtick");
    legend0.setAttribute("x",PAD_L); legend0.setAttribute("y",legendY+20);
    legend0.textContent = "0";
    svg.appendChild(legend0);

    var legendMax = document.createElementNS(svgns,"text");
    legendMax.setAttribute("class","gtick");
    legendMax.setAttribute("x",PAD_L+legendW); legendMax.setAttribute("y",legendY+20);
    legendMax.setAttribute("text-anchor","end");
    legendMax.textContent = maxCount+" cycles";
    svg.appendChild(legendMax);

    wrap.appendChild(svg);
    wrap.appendChild(tooltip);

    var total = cells.reduce(function(s,c){ return s+c.count; }, 0);
    var peak = cells.reduce(function(a,b){ return b.count>a.count ? b : a; }, cells[0]);
    card.querySelector('[data-stat="total"]').textContent = total;
    card.querySelector('[data-stat="peak-bin"]').textContent = peak.temp_bin+"°/"+peak.humidity_bin+"%";
    card.querySelector('[data-stat="peak-val"]').textContent = peak.count;
  }

  function shortDate(iso){
    var d = new Date(iso+"T00:00:00");
    var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return months[d.getMonth()] + " " + String(d.getDate()).padStart(2,"0");
  }

  function socColor(soc){
    var t = Math.max(0, Math.min(1, soc/100));
    var r = Math.round(17 + (210-17)*t);
    var g = Math.round(20 + (153-20)*t);
    var b = Math.round(18 + (34-18)*t);
    return "rgb("+r+","+g+","+b+")";
  }

  function buildBatteryHeatmap(cells){
    var card = document.getElementById("card-battery-heatmap");
    var wrap = card.querySelector(".chart-wrap");

    var dates = Array.from(new Set(cells.map(function(c){ return c.date; }))).sort();
    var rows = dates.length;
    var cols = 24;

    var lookup = {};
    cells.forEach(function(c){ lookup[c.date+"|"+c.hour] = c.soc; });

    var W=600, PAD_L=42, PAD_R=8, TOP_H=16, cellH=4;
    var GRID_H = rows*cellH;
    var LEGEND_GAP=16, LEGEND_H=8, LEGEND_LABEL_H=20, BOTTOM_PAD=8;
    var H = TOP_H + GRID_H + LEGEND_GAP + LEGEND_H + LEGEND_LABEL_H + BOTTOM_PAD;
    var gridW = W-PAD_L-PAD_R;
    var cellW = gridW/cols;
    var legendY = TOP_H+GRID_H+LEGEND_GAP;
    var legendW = gridW;

    var svgns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(svgns,"svg");
    svg.setAttribute("viewBox","0 0 "+W+" "+H);
    svg.setAttribute("preserveAspectRatio","none");

    var defs = document.createElementNS(svgns,"defs");
    var legendGrad = document.createElementNS(svgns,"linearGradient");
    legendGrad.setAttribute("id","legend-grad-soc");
    legendGrad.setAttribute("x1","0%"); legendGrad.setAttribute("y1","0%");
    legendGrad.setAttribute("x2","100%"); legendGrad.setAttribute("y2","0%");
    var lg1 = document.createElementNS(svgns,"stop"); lg1.setAttribute("offset","0%"); lg1.setAttribute("stop-color", socColor(0));
    var lg2 = document.createElementNS(svgns,"stop"); lg2.setAttribute("offset","100%"); lg2.setAttribute("stop-color", socColor(100));
    legendGrad.appendChild(lg1); legendGrad.appendChild(lg2);
    defs.appendChild(legendGrad);
    svg.appendChild(defs);

    [0,3,6,9,12,15,18,21].forEach(function(h){
      var txt = document.createElementNS(svgns,"text");
      txt.setAttribute("class","xtick");
      txt.setAttribute("x", PAD_L+h*cellW+cellW/2);
      txt.setAttribute("y", 10);
      txt.setAttribute("text-anchor","middle");
      txt.textContent = String(h).padStart(2,"0");
      svg.appendChild(txt);
    });

    var tooltip = document.createElement("div");
    tooltip.className = "tooltip";

    dates.forEach(function(dt,ri){
      for (var h=0; h<24; h++){
        var soc = lookup[dt+"|"+h];
        if (soc === undefined) continue;
        var x = PAD_L+h*cellW, y = TOP_H+ri*cellH;
        var rect = document.createElementNS(svgns,"rect");
        rect.setAttribute("x",x); rect.setAttribute("y",y);
        rect.setAttribute("width",cellW); rect.setAttribute("height",cellH);
        rect.setAttribute("fill", socColor(soc));
        svg.appendChild(rect);

        rect.addEventListener("mouseenter", function(dt,h,soc,x,y){
          return function(){
            var rectBox = svg.getBoundingClientRect();
            var scale = rectBox.width / W;
            tooltip.innerHTML = dt+' '+String(h).padStart(2,"0")+':00 &nbsp;<b>'+soc.toFixed(1)+'%</b>';
            tooltip.style.left = ((x+cellW/2)*scale)+"px";
            tooltip.style.top = (y*scale)+"px";
            tooltip.style.opacity = 1;
          };
        }(dt,h,soc,x,y));
        rect.addEventListener("mouseleave", function(){ tooltip.style.opacity = 0; });
      }

      if (ri % 14 === 0 || ri === rows-1){
        var label = document.createElementNS(svgns,"text");
        label.setAttribute("class","gtick");
        label.setAttribute("x",2);
        label.setAttribute("y", TOP_H+ri*cellH+cellH+2);
        label.textContent = shortDate(dt);
        svg.appendChild(label);
      }
    });

    var legendRect = document.createElementNS(svgns,"rect");
    legendRect.setAttribute("x",PAD_L); legendRect.setAttribute("y",legendY);
    legendRect.setAttribute("width",legendW); legendRect.setAttribute("height",LEGEND_H);
    legendRect.setAttribute("fill","url(#legend-grad-soc)");
    svg.appendChild(legendRect);

    var legend0 = document.createElementNS(svgns,"text");
    legend0.setAttribute("class","gtick");
    legend0.setAttribute("x",PAD_L); legend0.setAttribute("y",legendY+20);
    legend0.textContent = "0%";
    svg.appendChild(legend0);

    var legendMax = document.createElementNS(svgns,"text");
    legendMax.setAttribute("class","gtick");
    legendMax.setAttribute("x",PAD_L+legendW); legendMax.setAttribute("y",legendY+20);
    legendMax.setAttribute("text-anchor","end");
    legendMax.textContent = "100%";
    svg.appendChild(legendMax);

    wrap.appendChild(svg);
    wrap.appendChild(tooltip);

    var socs = cells.map(function(c){ return c.soc; });
    var latest = cells[cells.length-1].soc;
    card.querySelector('[data-stat="latest"]').textContent = latest.toFixed(1)+"%";
    card.querySelector('[data-stat="min"]').textContent = Math.min.apply(null,socs).toFixed(1)+"%";
    card.querySelector('[data-stat="max"]').textContent = Math.max.apply(null,socs).toFixed(1)+"%";
  }

  fetch("data/defrost_vs_temp.json").then(function(r){ return r.json(); })
    .then(function(d){ buildBarChart("defrostTemp", d); })
    .catch(function(err){ console.error("failed to load defrost_vs_temp.json", err); });

  fetch("data/defrost_vs_humidity.json").then(function(r){ return r.json(); })
    .then(function(d){ buildBarChart("defrostRh", d); })
    .catch(function(err){ console.error("failed to load defrost_vs_humidity.json", err); });

  fetch("data/compressor_rpm.json").then(function(r){ return r.json(); })
    .then(function(d){ buildRpmChart(d); })
    .catch(function(err){ console.error("failed to load compressor_rpm.json", err); });

  fetch("data/defrost_heatmap.json").then(function(r){ return r.json(); })
    .then(function(d){ buildHeatmap(d); })
    .catch(function(err){ console.error("failed to load defrost_heatmap.json", err); });

  fetch("data/battery_heatmap.json").then(function(r){ return r.json(); })
    .then(function(d){ buildBatteryHeatmap(d); })
    .catch(function(err){ console.error("failed to load battery_heatmap.json", err); });
})();
