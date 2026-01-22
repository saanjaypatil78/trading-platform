
import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Plus, Trash2, Play } from 'lucide-react';
import { fetchWithFailover } from '../lib/api';

// --- Types ---

type Operator = 'AND' | 'OR';
type Comparison = '>' | '<' | '>=' | '<=' | '==' | '!=';

interface Rule {
    id: string;
    field: string;
    op: Comparison;
    value: string;
}

interface RuleGroup {
    id: string;
    operator: Operator;
    rules: (Rule | RuleGroup)[];
}

// --- Helper Functions ---

const createRule = (): Rule => ({
    id: Math.random().toString(36).substr(2, 9),
    field: 'RSI',
    op: '>',
    value: '70'
});

const createGroup = (): RuleGroup => ({
    id: Math.random().toString(36).substr(2, 9),
    operator: 'AND',
    rules: [createRule()]
});

// --- Components ---

const ComparisonSelector = ({ value, onChange }: { value: Comparison, onChange: (v: Comparison) => void }) => (
    <select
        value={value}
        onChange={(e) => onChange(e.target.value as Comparison)}
        className="rounded border p-1 text-sm bg-background"
    >
        <option value=">">&gt;</option>
        <option value="<">&lt;</option>
        <option value=">=">&gt;=</option>
        <option value="<=">&lt;=</option>
        <option value="==">=</option>
        <option value="!=">!=</option>
    </select>
);

const FieldSelector = ({ value, onChange }: { value: string, onChange: (v: string) => void }) => (
    <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border p-1 text-sm bg-background min-w-[100px]"
    >
        <option value="RSI">RSI</option>
        <option value="SMA_20">SMA 20</option>
        <option value="SMA_50">SMA 50</option>
        <option value="SMA_200">SMA 200</option>
        <option value="close">Close Price</option>
        <option value="volume">Volume</option>
    </select>
);

export function ConditionBuilder() {
    // Root group
    const [root, setRoot] = useState<RuleGroup>(createGroup());
    const [result, setResult] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const updateGroup = (groupId: string, newGroup: RuleGroup, current = root): RuleGroup => {
        if (current.id === groupId) return newGroup;
        // Deep search
        const updatedRules = current.rules.map(r => {
            if ('operator' in r) return updateGroup(groupId, newGroup, r as RuleGroup);
            return r;
        });
        return { ...current, rules: updatedRules };
    };

    // Very simplified update logic for demo (only works for root direct children usually unless full recursive handler passes down)
    // Actually, creating a recursive component 'RuleGroupRenderer' is cleaner.

    // Let's reimplement with clean recursion.
    // We need a global update function we can pass down.

    const updateNode = (nodeId: string, transform: (node: Rule | RuleGroup) => Rule | RuleGroup) => {
        const recursiveUpdate = (current: RuleGroup): RuleGroup => {
            if (current.id === nodeId) return transform(current) as RuleGroup;

            const updatedRules = current.rules.map(r => {
                if ('operator' in r) { // It's a group
                    if (r.id === nodeId) return transform(r);
                    return recursiveUpdate(r);
                }
                if (r.id === nodeId) return transform(r); // It's a rule
                return r;
            });
            return { ...current, rules: updatedRules };
        };

        // If root is the target
        if (root.id === nodeId) setRoot(transform(root) as RuleGroup);
        else setRoot(recursiveUpdate(root));
    };

    const addRuleToGroup = (groupId: string) => {
        updateNode(groupId, (node) => {
            const group = node as RuleGroup;
            return { ...group, rules: [...group.rules, createRule()] };
        });
    };

    const deleteNode = (nodeId: string) => {
        // Special case: deleting root node not allowed or handled differently
        if (nodeId === root.id) return;

        const recursiveDelete = (current: RuleGroup): RuleGroup => {
            const filteredRules = current.rules.filter(r => r.id !== nodeId);
            const mappedRules = filteredRules.map(r => {
                if ('operator' in r) return recursiveDelete(r);
                return r;
            });
            return { ...current, rules: mappedRules };
        };
        setRoot(recursiveDelete(root));
    };

    const runScan = async () => {
        setLoading(true);
        setResult(null);
        try {
            // Transform to backend format (strip IDs)
            const clean = JSON.parse(JSON.stringify(root, (key, value) => {
                if (key === 'id') return undefined; // Remove ID
                return value;
            }));

            const res = await fetchWithFailover('/api/v1/scanner/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ logic: clean })
            });
            const data = await res.json();
            setResult(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    // --- Recursive Renderer ---
    const RenderNode = ({ node, depth = 0 }: { node: Rule | RuleGroup, depth?: number }) => {
        if ('operator' in node) {
            // It's a Group
            const group = node as RuleGroup;
            return (
                <div className={`p-4 rounded-lg border ${depth % 2 === 0 ? 'bg-secondary/10 border-primary/20' : 'bg-background border-border'} ml-4 space-y-3`}>
                    <div className="flex items-center gap-2 mb-2">
                        <select
                            value={group.operator}
                            onChange={(e) => updateNode(group.id, n => ({ ...n, operator: e.target.value as Operator }))}
                            className="bg-primary text-primary-foreground text-xs font-bold px-2 py-1 rounded"
                        >
                            <option value="AND">AND</option>
                            <option value="OR">OR</option>
                        </select>
                        <div className="flex-1" />
                        <Button variant="ghost" size="sm" onClick={() => addRuleToGroup(group.id)}><Plus className="h-4 w-4 mr-1" /> Add Rule</Button>
                        {depth > 0 && (
                            <Button variant="ghost" size="icon" onClick={() => deleteNode(group.id)} className="text-destructive"><Trash2 className="h-4 w-4" /></Button>
                        )}
                    </div>

                    <div className="space-y-2">
                        {group.rules.map(child => (
                            <RenderNode key={child.id} node={child} depth={depth + 1} />
                        ))}
                    </div>
                </div>
            );
        } else {
            // It's a Rule
            const rule = node as Rule;
            return (
                <div className="flex items-center gap-2 p-2 rounded bg-card border shadow-sm ml-4">
                    <FieldSelector
                        value={rule.field}
                        onChange={(v) => updateNode(rule.id, n => ({ ...n, field: v }))}
                    />
                    <ComparisonSelector
                        value={rule.op}
                        onChange={(v) => updateNode(rule.id, n => ({ ...n, op: v }))}
                    />
                    <input
                        type="number"
                        value={rule.value}
                        onChange={(e) => updateNode(rule.id, n => ({ ...n, value: e.target.value }))}
                        className="w-20 rounded border p-1 text-sm bg-background"
                    />
                    <Button variant="ghost" size="icon" onClick={() => deleteNode(rule.id)} className="ml-auto text-muted-foreground hover:text-destructive">
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            );
        }
    };

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="flex justify-between items-center">
                    <span>Market Scanner Builder</span>
                    <Button onClick={runScan} disabled={loading} className="gap-2">
                        <Play className="h-4 w-4" />
                        {loading ? 'Scanning...' : 'Run Scan'}
                    </Button>
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="space-y-6">
                    <RenderNode node={root} />

                    {result && (
                        <div className="mt-6 border-t pt-4">
                            <h3 className="font-bold mb-2">Scan Results ({result.matches?.length || 0})</h3>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                                {result.matches?.map((m: any, i: number) => (
                                    <Badge key={i} variant="secondary" className="justify-center py-1">
                                        {m.symbol}
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
