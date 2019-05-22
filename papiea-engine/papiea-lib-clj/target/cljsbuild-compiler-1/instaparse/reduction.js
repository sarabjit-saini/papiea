// Compiled by ClojureScript 1.10.439 {:target :nodejs}
goog.provide('instaparse.reduction');
goog.require('cljs.core');
goog.require('instaparse.auto_flatten_seq');
goog.require('instaparse.util');
instaparse.reduction.singleton_QMARK_ = (function instaparse$reduction$singleton_QMARK_(s){
return ((cljs.core.seq.call(null,s)) && (cljs.core.not.call(null,cljs.core.next.call(null,s))));
});
instaparse.reduction.red = (function instaparse$reduction$red(parser,f){
return cljs.core.assoc.call(null,parser,new cljs.core.Keyword(null,"red","red",-969428204),f);
});
instaparse.reduction.raw_non_terminal_reduction = new cljs.core.PersistentArrayMap(null, 1, [new cljs.core.Keyword(null,"reduction-type","reduction-type",-488293450),new cljs.core.Keyword(null,"raw","raw",1604651272)], null);
instaparse.reduction.HiccupNonTerminalReduction = (function instaparse$reduction$HiccupNonTerminalReduction(key){
return new cljs.core.PersistentArrayMap(null, 2, [new cljs.core.Keyword(null,"reduction-type","reduction-type",-488293450),new cljs.core.Keyword(null,"hiccup","hiccup",1218876238),new cljs.core.Keyword(null,"key","key",-1516042587),key], null);
});
instaparse.reduction.EnliveNonTerminalReduction = (function instaparse$reduction$EnliveNonTerminalReduction(key){
return new cljs.core.PersistentArrayMap(null, 2, [new cljs.core.Keyword(null,"reduction-type","reduction-type",-488293450),new cljs.core.Keyword(null,"enlive","enlive",1679023921),new cljs.core.Keyword(null,"key","key",-1516042587),key], null);
});
instaparse.reduction.reduction_types = new cljs.core.PersistentArrayMap(null, 2, [new cljs.core.Keyword(null,"hiccup","hiccup",1218876238),instaparse.reduction.HiccupNonTerminalReduction,new cljs.core.Keyword(null,"enlive","enlive",1679023921),instaparse.reduction.EnliveNonTerminalReduction], null);
instaparse.reduction.node_builders = new cljs.core.PersistentArrayMap(null, 2, [new cljs.core.Keyword(null,"enlive","enlive",1679023921),(function (tag,item){
return new cljs.core.PersistentArrayMap(null, 2, [new cljs.core.Keyword(null,"tag","tag",-1290361223),tag,new cljs.core.Keyword(null,"content","content",15833224),(new cljs.core.List(null,item,null,(1),null))], null);
}),new cljs.core.Keyword(null,"hiccup","hiccup",1218876238),(function (tag,item){
return new cljs.core.PersistentVector(null, 2, 5, cljs.core.PersistentVector.EMPTY_NODE, [tag,item], null);
})], null);
instaparse.reduction.standard_non_terminal_reduction = new cljs.core.Keyword(null,"hiccup","hiccup",1218876238);
instaparse.reduction.apply_reduction = (function instaparse$reduction$apply_reduction(f,result){
var G__7348 = new cljs.core.Keyword(null,"reduction-type","reduction-type",-488293450).cljs$core$IFn$_invoke$arity$1(f);
var G__7348__$1 = (((G__7348 instanceof cljs.core.Keyword))?G__7348.fqn:null);
switch (G__7348__$1) {
case "raw":
return instaparse.auto_flatten_seq.conj_flat.call(null,instaparse.auto_flatten_seq.EMPTY,result);

break;
case "hiccup":
return instaparse.auto_flatten_seq.convert_afs_to_vec.call(null,instaparse.auto_flatten_seq.conj_flat.call(null,instaparse.auto_flatten_seq.auto_flatten_seq.call(null,new cljs.core.PersistentVector(null, 1, 5, cljs.core.PersistentVector.EMPTY_NODE, [new cljs.core.Keyword(null,"key","key",-1516042587).cljs$core$IFn$_invoke$arity$1(f)], null)),result));

break;
case "enlive":
var content = instaparse.auto_flatten_seq.conj_flat.call(null,instaparse.auto_flatten_seq.EMPTY,result);
return new cljs.core.PersistentArrayMap(null, 2, [new cljs.core.Keyword(null,"tag","tag",-1290361223),new cljs.core.Keyword(null,"key","key",-1516042587).cljs$core$IFn$_invoke$arity$1(f),new cljs.core.Keyword(null,"content","content",15833224),(((cljs.core.count.call(null,content) === (0)))?null:content)], null);

break;
default:
return f.call(null,result);

}
});
instaparse.reduction.apply_standard_reductions = (function instaparse$reduction$apply_standard_reductions(var_args){
var G__7351 = arguments.length;
switch (G__7351) {
case 1:
return instaparse.reduction.apply_standard_reductions.cljs$core$IFn$_invoke$arity$1((arguments[(0)]));

break;
case 2:
return instaparse.reduction.apply_standard_reductions.cljs$core$IFn$_invoke$arity$2((arguments[(0)]),(arguments[(1)]));

break;
default:
throw (new Error(["Invalid arity: ",cljs.core.str.cljs$core$IFn$_invoke$arity$1(arguments.length)].join('')));

}
});

instaparse.reduction.apply_standard_reductions.cljs$core$IFn$_invoke$arity$1 = (function (grammar){
return instaparse.reduction.apply_standard_reductions.call(null,instaparse.reduction.standard_non_terminal_reduction,grammar);
});

instaparse.reduction.apply_standard_reductions.cljs$core$IFn$_invoke$arity$2 = (function (reduction_type,grammar){
var temp__5455__auto__ = instaparse.reduction.reduction_types.call(null,reduction_type);
if(cljs.core.truth_(temp__5455__auto__)){
var reduction = temp__5455__auto__;
return cljs.core.into.call(null,cljs.core.PersistentArrayMap.EMPTY,(function (){var iter__4434__auto__ = ((function (reduction,temp__5455__auto__){
return (function instaparse$reduction$iter__7352(s__7353){
return (new cljs.core.LazySeq(null,((function (reduction,temp__5455__auto__){
return (function (){
var s__7353__$1 = s__7353;
while(true){
var temp__5457__auto__ = cljs.core.seq.call(null,s__7353__$1);
if(temp__5457__auto__){
var s__7353__$2 = temp__5457__auto__;
if(cljs.core.chunked_seq_QMARK_.call(null,s__7353__$2)){
var c__4432__auto__ = cljs.core.chunk_first.call(null,s__7353__$2);
var size__4433__auto__ = cljs.core.count.call(null,c__4432__auto__);
var b__7355 = cljs.core.chunk_buffer.call(null,size__4433__auto__);
if((function (){var i__7354 = (0);
while(true){
if((i__7354 < size__4433__auto__)){
var vec__7356 = cljs.core._nth.call(null,c__4432__auto__,i__7354);
var k = cljs.core.nth.call(null,vec__7356,(0),null);
var v = cljs.core.nth.call(null,vec__7356,(1),null);
cljs.core.chunk_append.call(null,b__7355,(cljs.core.truth_(new cljs.core.Keyword(null,"red","red",-969428204).cljs$core$IFn$_invoke$arity$1(v))?new cljs.core.PersistentVector(null, 2, 5, cljs.core.PersistentVector.EMPTY_NODE, [k,v], null):new cljs.core.PersistentVector(null, 2, 5, cljs.core.PersistentVector.EMPTY_NODE, [k,cljs.core.assoc.call(null,v,new cljs.core.Keyword(null,"red","red",-969428204),reduction.call(null,k))], null)));

var G__7363 = (i__7354 + (1));
i__7354 = G__7363;
continue;
} else {
return true;
}
break;
}
})()){
return cljs.core.chunk_cons.call(null,cljs.core.chunk.call(null,b__7355),instaparse$reduction$iter__7352.call(null,cljs.core.chunk_rest.call(null,s__7353__$2)));
} else {
return cljs.core.chunk_cons.call(null,cljs.core.chunk.call(null,b__7355),null);
}
} else {
var vec__7359 = cljs.core.first.call(null,s__7353__$2);
var k = cljs.core.nth.call(null,vec__7359,(0),null);
var v = cljs.core.nth.call(null,vec__7359,(1),null);
return cljs.core.cons.call(null,(cljs.core.truth_(new cljs.core.Keyword(null,"red","red",-969428204).cljs$core$IFn$_invoke$arity$1(v))?new cljs.core.PersistentVector(null, 2, 5, cljs.core.PersistentVector.EMPTY_NODE, [k,v], null):new cljs.core.PersistentVector(null, 2, 5, cljs.core.PersistentVector.EMPTY_NODE, [k,cljs.core.assoc.call(null,v,new cljs.core.Keyword(null,"red","red",-969428204),reduction.call(null,k))], null)),instaparse$reduction$iter__7352.call(null,cljs.core.rest.call(null,s__7353__$2)));
}
} else {
return null;
}
break;
}
});})(reduction,temp__5455__auto__))
,null,null));
});})(reduction,temp__5455__auto__))
;
return iter__4434__auto__.call(null,grammar);
})());
} else {
return instaparse.util.throw_illegal_argument_exception.call(null,"Invalid output format ",reduction_type,". Use :enlive or :hiccup.");
}
});

instaparse.reduction.apply_standard_reductions.cljs$lang$maxFixedArity = 2;


//# sourceMappingURL=reduction.js.map