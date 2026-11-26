'use strict';
// Shared by the workstation and assessment API. Numeric zero is an observed value.
const ResearchScore = {
  limits: {age:[18,110], sex:[0,1], cp:[1,4], trestbps:[70,260], chol:[80,700], fbs:[0,1], restecg:[0,2], thalach:[40,230], exang:[0,1], oldpeak:[0,8], slope:[1,3], ca:[0,3], thal:[3,7]},
  valid(k,v) {
    const [lo,hi] = this.limits[k];
    return Number.isFinite(v) && v>=lo && v<=hi && (k==='oldpeak' ? Number.isInteger(v*10) : Number.isInteger(v)) && (k!=='thal' || [3,6,7].includes(v));
  },
  predict(w,p) {
    if (!w || !p || Object.keys(this.limits).some(k=>!this.valid(k,p[k]))) return NaN;
    const x=w.numeric.map((k,i)=>(p[k]-w.num_mean[i])/w.num_scale[i]);
    w.categorical.forEach((k,i)=>w.cat_categories[i].forEach(v=>x.push(Number(p[k]===v))));
    const logit=x.reduce((sum,v,i)=>sum+v*w.coef[i],w.intercept);
    return 1/(1+Math.exp(-logit));
  }
};
if (typeof module !== 'undefined') module.exports = ResearchScore;
